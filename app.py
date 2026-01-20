from datetime import datetime
import pandas as pd
import io
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, send_file
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tools.agent_tools import list_tables, execute_sql, create_visualization, generate_plot_image
from cache.cache_manager import CacheManager
from tools.document_rag import initialize_document_store, search_documents
import os
import json
from dotenv import load_dotenv

load_dotenv()

def get_bq_client(project):
    """Returns a BigQuery client, using environment variable JSON if available."""
    json_creds = os.environ.get('GCP_SERVICE_ACCOUNT_JSON')
    if json_creds:
        from google.oauth2 import service_account
        from google.cloud import bigquery
        try:
            info = json.loads(json_creds)
            credentials = service_account.Credentials.from_service_account_info(info)
            return bigquery.Client(project=project, credentials=credentials)
        except Exception as e:
            print(f"Error loading GCP_SERVICE_ACCOUNT_JSON: {e}")
    # Fallback to default (works locally if GOOGLE_APPLICATION_CREDENTIALS is set)
    from google.cloud import bigquery
    return bigquery.Client(project=project)

# Initialize document vector store
print("Initializing document vector store...")
initialize_document_store()
print("Document store ready")

app = Flask(__name__)
app.secret_key = 'agency_os_super_secret_key' # In production, use environment variable


# --- CONFIGURATION ---
# LLM Setup
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, verbose=True)

#tool binding
tools = [list_tables, execute_sql, create_visualization, search_documents]
llm_with_tools = llm.bind_tools(tools)

chat_histories = {}

#to stop hallucinantion on date part, need to add todays date
todays_date = datetime.now().strftime("%Y-%m-%d")

system_prompt = (
     "You are a helpful data assistant connected to a BigQuery database. "
     "You have full access to the database via your tools. Do not say you don't have access.\n"
     "RULES:\n"
     "1. DATASET: Always search answers from the `hackathon_data` dataset.\n"
     "2. FIRST STEP: You MUST use `list_tables` to see the valid table names. Do NOT guess table names like 'application_sample'.\n"
     "3. TABLE MAPPINGS: Use these specific tables when the user refers to these terms:\n"
     "   - `application_table`: applications, application, applicants\n"
     "   - `base_branch_table`: branch, branches\n"
     "   - `base_contact_table`: contacts, contact, clients, client, customer\n"
     "   - `crm_user`: user, users\n"
     "   - `deals_applications_table`: applications in deal, applications of client, applicants deal\n"
     "   - `enquiry_deals_applications_table`: applications based on enquiry, applications based on deals, deals based on enquiry, enquiry\n"
     "   - `enquiry_table`: enquiry\n"
     "   - `feedback_questions_table`: feedback questions, questions in feedback\n"
     "   - `feedback_table`: feedbacks from office visit client, feedbacks, feedback\n"
     "   - `office_visit_table`: office visits, branch visits, query from branches, client queries\n"
     "4. JOINS: If required, perform cross-table information gathering by joining tables based on their IDs.\n"
     "5. Use `execute_sql` to get data. Always use the dataset `hackathon_data`.\n"
     "   - DATE HANDLING: Dates are stored as STRINGS (e.g. '2025-12-01'). You MUST cast them using `CAST(column AS DATE)` or `PARSE_DATE('%Y-%m-%d', column)` before using functions like `EXTRACT`.\n"
     "6. VISUALIZATIONS: \n"
     "   - PREFER interactive format over static images.\n"
     "   - For Comparison/Trends (Bar, Line, Pie, Scatter): Return a JSON object with `visualization_type` (e.g. 'bar', 'line'), `visualization_title` (a clear title), and `data_query` (SQL query). \n"
     "   - IMPORTANT: SQL query for charts should return the CATEGORY/LABEL as the first column and the VALUE/COUNT as the second column. \n"
     "   - For Processes/Workflows (Flowchart): Return a JSON object with `visualization_type`: 'flowchart' and `data`: 'MERMAID_SYNTAX'.\n"
     "7. DO NOT generate ASCII tables or markdown tables for data that should be graphed. Always use the JSON visualization format for chart requests.\n"
     "8. If asking for a comparison (e.g., 'compare A and B'), query data for both and return the visualization JSON.\n"
     "9. ALWAYS answer based on the data returned by the tools. Do not make up facts.\n"
     "10. If a tool returns an error, try to fix the query and try again.\n"
     "11. Visualizations are rendered directly in the chat window. DO NOT say they will be in a separate window.\n"
     "12. Based on the previous output and steps, try to continue the conversation with memory saved.\n"
     "13. DOCUMENT SEARCH: Use `search_documents` when users ask about uploaded documents, workflows, processes, or any information from PDF files.\n"
     "14. You can combine database queries with document searches to provide comprehensive answers.\n"
     "15. If asked beyond the hackathon_data and documents, deny saying 'I am not trained to communicate on these topics'.\n"
     "16. MERMAID/FLOWCHART SYNTAX RULES:\n"
     "    - Use `graph TD` or `graph LR`.\n"
     "    - Wrap node labels in double quotes. Example: A[\"Start Process\"]\n"
     "    - Do NOT use double quotes inside the label. Use single quotes if needed. Example: B[\"Select 'Option 1'\"]\n"
     "    - Return as unstructured string in the `data` field of the JSON. Ensure newlines are encoded as `\\n`."
     "17. memorize eveything from the last converstation and try to continue the conversation with memory saved.\n"
     "18. Always try to continue the conversation with memory saved. Ask each time for further assistance based on last conversation\n"
     "19. When asked about gramatical noun in the chat always consider canonical status rules , here left side values are database status and right side values are their sysnonyms:\n"
     "    - Enquiry Status Mapping:\n"
     "        - new, contacted, evaluating : Open\n"
     "        - converted : Converted\n"
     "        - assessing, future lead, engage immediately, accessing : Qualified\n"
     "        - financial limitations, service unavailable, personal circumstances, not a fit, incorrect information : Disqualified ,ineligible\n"
     "        - interest withdrawn, changed decision, unresponsive, competitor selected : Lost\n"
     "        - archived : Archived\n"
     "    - Application Status Mapping:\n"
     "        - In Progress: active, ongoing, processing, open application, on track, open\n"
     "        - Discontinued: convertinactive, in-active, withdrawn, cancelled, closed, terminateded\n"
     "        - Completed: completed, finished, closed\n"
     "    - Office Visit Status Mapping:\n"
     "        - Pending: active, ongoing, processing, open application, on track, open\n"
     "        - Unattended: convertinactive, in-active, withdrawn, cancelled, closed, terminateded\n"
     "        - Waiting: completed, finished, closed\n"
     "        - Completed: completed, finished, closed\n"
     "        - Attending: attending, in session, ongoing, active, participating\n"
     "    - Deal Status Mapping:\n"
     "        - discovery: new deal, converted enquiry, not started\n"
     "        - in-progress: active\n"
     "        - lost: inactive, in-active, unsuccessful\n"
     "        - completed: completed, won, win, success\n"
     "20. During answering dont reference based on the database column names and document names.\n"
     "21. when asked about separate tables ,graphs, chats or flowchart render it separately as asked.\n"
     "22. Do NOT say 'Based on the available document' or similar phrases. Provide the answer directly and concisely.\n"
     "23. ACCESS CONTROL & SQL TIPS: You are strictly limited to data from specific branches. \n"
     "24. Your primary branch is: {primary_branch}. \n"
     "25. Your currently allowed branches (including primary and secondary) are: {allowed_branches}. \n"
     "26. You MUST filter all SQL queries by these branches. IMPORTANT: Use the following specific columns per table:\n"
     "   - `application_table`: Branch: `branch`. Date: `Added_Date`. Status: `Status` (Values: 'Completed', 'In Progress', 'Discontinued').\n"
     "   - `enquiry_table`: Branch: `branch`. Date: `created_at`. Status: `status`.\n"
     "   - `office_visits_table`: Branch: `visited_branch_name`. Date: `visit_date`.\n"
     "   - `deals_applications_table`: Branch: `deal_belongs_to_branch` or `processing_branch_name`. Date: `deal_created_at`. Status: `deal_status` or `application_status`.\n"
     "27. BIGQUERY DATE TIPS: These columns are DATETIME. DO NOT use `PARSE_DATE` on them. Use `EXTRACT(MONTH FROM Added_Date)` or `FORMAT_DATETIME('%B', Added_Date)` for filtering by month name.\n"
     "28. If you need to join tables to find the branch affiliation, do so.\n"
     "29. If a user asks for data outside these branches, politely state that you only have access to their assigned branches: {allowed_branches}.\n"
     "30. When asked about your assigned branches, list both your primary branch and your secondary branches clearly.\n"
     "31. When user's branch is All branches, it mean he has access to all the available branches\n"
     "32. When asked about the assignee, always consider the user name and user's primary branch\n"
     "33. Consider typo to the closest meaning\n"
     "34. If the output token is maxed out then prompty say, the request is too big for me to continue\n"
     f"Always consider todays date in your answer, when asked about the date consider {todays_date}\n"
)

# Create Agent (returns a Graph)
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])
agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, return_intermediate_steps=True)

@app.route('/')
def home():
    if 'user_email' not in session:
        return redirect(url_for('login_page'))
    return render_template('index.html', user_email=session.get('user_email'))

@app.route('/login')
def login_page():
    if 'user_email' in session:
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/api/login', methods=['POST'])
def login_api():
    try:
        data = request.json
        email = data.get('email')
        
        if not email:
            return jsonify({'success': False, 'error': 'Email is required'}), 400
            
        # Verify against BigQuery
        from google.cloud import bigquery
        bq_client = get_bq_client(project='expert-hackathon-2026')
        
        query = """
            SELECT user_email, primary_branch_name, branches
            FROM `hackathon_data.crm_users` 
            WHERE user_email = @email
            AND active_status = 'active'
            LIMIT 1
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", email)
            ]
        )
        
        query_job = bq_client.query(query, job_config=job_config)
        results = list(query_job.result())
        
        if results:
            session['user_email'] = results[0].user_email
            session['primary_branch'] = results[0].primary_branch_name
            session['allowed_branches_raw'] = results[0].branches
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Account not found or inactive'}), 401
            
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'success': False, 'error': 'Server error'}), 500

@app.route('/api/branches', methods=['GET'])
def get_branches():
    """
    Fetch branch locations from BigQuery and return with coordinates.
    Uses predefined coordinates based on branch names.
    """
    try:
        from google.cloud import bigquery
        
        bq_client = get_bq_client(project='expert-hackathon-2026')
        
        # Predefined coordinates for known branch locations
        branch_coordinates = {
            'johannesburg': {'lat': -26.2041, 'lng': 28.0473},
            'lagos': {'lat': 6.5244, 'lng': 3.3792},
            'yaba': {'lat': 6.5244, 'lng': 3.3792},
            'port harcourt': {'lat': 4.8156, 'lng': 7.0498},
            'nairobi': {'lat': -1.2921, 'lng': 36.8219},
            'accra': {'lat': 5.6037, 'lng': -0.1870},
            'kampala': {'lat': 0.3476, 'lng': 32.5825},
            'dar es salaam': {'lat': -6.7924, 'lng': 39.2083},
            'kigali': {'lat': -1.9706, 'lng': 30.1044},
            'kathmandu': {'lat': 27.7172, 'lng': 85.3240},
            'putalisadak': {'lat': 27.7172, 'lng': 85.3240},
            'pokhara': {'lat': 28.2096, 'lng': 83.9856},
            'chitwan': {'lat': 27.5291, 'lng': 84.3542},
            'sydney': {'lat': -33.8688, 'lng': 151.2093},
            'parramatta': {'lat': -33.8151, 'lng': 151.0000},
            'melbourne': {'lat': -37.8136, 'lng': 144.9631},
            'brisbane': {'lat': -27.4698, 'lng': 153.0251},
            'perth': {'lat': -31.9505, 'lng': 115.8605},
            'adelaide': {'lat': -34.9285, 'lng': 138.6007},
            'abuja': {'lat': 9.0765, 'lng': 7.3986},
            'ibadan': {'lat': 7.3775, 'lng': 3.9470},
            'kano': {'lat': 12.0022, 'lng': 8.5920},
        }
        
        # Query branch data
        query = """
            SELECT 
                branch_id,
                branch_name,
                branch_address
            FROM `hackathon_data.base_branch_table`
            LIMIT 50
        """
        
        results = bq_client.query(query).result()
        branches = []
        
        for row in results:
            branch_name_lower = row.branch_name.lower() if row.branch_name else ''
            
            # Find matching coordinates
            coords = None
            
            # Helper to check if any key matches
            def get_coords(text):
                if not text: return None
                text = text.lower()
                for key, value in branch_coordinates.items():
                    if key in text:
                        return value
                return None

            # 1. Try matching by Name
            coords = get_coords(row.branch_name)
            
            # 2. If not found, try matching by Address
            if not coords:
                coords = get_coords(row.branch_address)
            
            # Only add branches with valid coordinates
            if coords:
                branches.append({
                    'id': row.branch_id,
                    'name': row.branch_name,
                    'address': row.branch_address,
                    'lat': coords['lat'],
                    'lng': coords['lng']
                })
        
        return jsonify({
            'success': True,
            'branches': branches,
            'count': len(branches)
        })
        
    except Exception as e:
        print(f"Error fetching branches: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'branches': []
        })

@app.route('/api/profile', methods=['GET'])
def get_user_profile():
    """
    Fetch user profile with primary and secondary branches from BigQuery.
    """
    try:
        if 'user_email' not in session:
            return jsonify({'success': False, 'error': 'Not logged in'}), 401
            
        user_email = session['user_email']
        
        # Check session first
        primary_branch = session.get('primary_branch')
        all_branches_str = session.get('allowed_branches_raw')
        
        if primary_branch is None or all_branches_str is None:
            # Fallback to BigQuery if session data is missing
            from google.cloud import bigquery
            bq_client = get_bq_client(project='expert-hackathon-2026')
            
            query = """
                SELECT primary_branch_name, branches 
                FROM `hackathon_data.crm_users` 
                WHERE user_email = @email
                LIMIT 1
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("email", "STRING", user_email)
                ]
            )
            
            query_job = bq_client.query(query, job_config=job_config)
            results = list(query_job.result())
            
            if results:
                row = results[0]
                primary_branch = row.primary_branch_name
                all_branches_str = row.branches or ""
                # Update session
                session['primary_branch'] = primary_branch
                session['allowed_branches_raw'] = all_branches_str
            else:
                return jsonify({'success': False, 'error': 'User profile not found'}), 404
        
        # Parse branches string (comma separated)
        all_branches = [b.strip() for b in all_branches_str.split(',') if b.strip()]
        
        # Secondary branches are those in the list that aren't the primary one
        secondary_branches = [b for b in all_branches if b.lower() != (primary_branch or "").lower()]
        
        return jsonify({
            'success': True,
            'primary_branch': primary_branch,
            'secondary_branches': secondary_branches
        })
            
    except Exception as e:
        print(f"Error fetching profile: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    user_msg = request.json.get("message")
    if not user_msg:
        return jsonify({"response": "Please enter a message."})

    try:
        # Get User ID for history
        user_id = session.get('user_email', 'default_user')
        
        # Enforce Branch Access Control
        primary_branch = session.get('primary_branch')
        allowed_branches_raw = session.get('allowed_branches_raw')
        
        if (primary_branch is None or allowed_branches_raw is None) and 'user_email' in session:
            # Fetch branches if not in session (for existing sessions)
            from google.cloud import bigquery
            bq_client = get_bq_client(project='expert-hackathon-2026')
            query = "SELECT primary_branch_name, branches FROM `hackathon_data.crm_users` WHERE user_email = @email LIMIT 1"
            job_config = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter("email", "STRING", user_id)])
            results = list(bq_client.query(query, job_config=job_config).result())
            if results:
                primary_branch = results[0].primary_branch_name
                allowed_branches_raw = results[0].branches
                session['primary_branch'] = primary_branch
                session['allowed_branches_raw'] = allowed_branches_raw
        
        # Format allowed branches for the prompt
        if allowed_branches_raw:
             # Split, strip, and format as quoted list
             branches = [b.strip() for b in allowed_branches_raw.split(',') if b.strip()]
             allowed_branches_str = ", ".join([f"'{b}'" for b in branches])
        else:
             allowed_branches_str = f"'{primary_branch}'" if primary_branch else "'None'"

        if user_id not in chat_histories:
            chat_histories[user_id] = []

        # Check Cache for full agent response
        # We use a composite key of user_msg and history
        cache_manager = CacheManager()
        cache_data = {"input": user_msg, "allowed_branches": allowed_branches_str, "primary_branch": primary_branch or ""}
        cached_response = cache_manager.get("agent_invoke", cache_data)
        
        if cached_response:
             print("[CACHE HIT] Agent Response")
             result = cached_response
             # Update history even on cache hit so context builds up
             chat_histories[user_id].extend([
                 HumanMessage(content=user_msg),
                 AIMessage(content=result.get("output", ""))
             ])
        else:
             print("[CACHE MISS] Agent Response using History")
             # Use the history in the invoke
             current_history = chat_histories[user_id]
             
             try:
                 result = agent_executor.invoke({
                    "input": user_msg,
                    "chat_history": current_history,
                    "allowed_branches": allowed_branches_str,
                    "primary_branch": primary_branch or "None"
                 })
             except Exception as e:
                 error_str = str(e).lower()
                 if "max_output_tokens" in error_str or "max tokens" in error_str or "finish_reason: 1" in error_str:
                     result = {"output": "The request is too big for me to continue. Please try asking a more specific question."}
                 elif "quota" in error_str or "429" in error_str:
                     result = {"output": "I am currently receiving too many requests. Please wait a moment and try again."}
                 else:
                     print(f"Agent execution error: {e}")
                     result = {"output": "I encountered an error while processing your request. Please try again or rephrase your question."}
             
             # Append to history
             chat_histories[user_id].extend([
                 HumanMessage(content=user_msg),
                 AIMessage(content=result.get("output", ""))
             ])
                          
             # Let's clean intermediate steps for caching
             clean_steps = []
             for action, observation in result.get("intermediate_steps", []):
                 # simplify action
                 clean_action = {
                     "tool": action.tool,
                     "tool_input": action.tool_input,
                     "log": action.log
                 }
                 clean_steps.append((clean_action, observation))
                 
             clean_result = {
                 "output": result.get("output"),
                 "intermediate_steps": clean_steps
             }
             
             # We store THIS clean result
             cache_manager.set("agent_invoke", cache_data, clean_result)
             
             # We use the original result for this turn
                
        final_answer = result.get("output", "")
        intermediate_steps = result.get("intermediate_steps", [])
        
        # Handle cases where final_answer is a list (newer LangChain versions / Google GenAI)
        if isinstance(final_answer, list):
            cleaned_parts = []
            for item in final_answer:
                # If item is a dict (e.g. Generation object), try to extract 'text'
                if isinstance(item, dict):
                    if "text" in item:
                        cleaned_parts.append(item["text"])
                    # Ignore other keys like 'extras', 'index', 'safety_ratings'
                # If item is an object with 'text' attribute (Pydantic model)
                elif hasattr(item, "text"):
                     cleaned_parts.append(item.text)
                # If string, use directly
                elif isinstance(item, str):
                    cleaned_parts.append(item)
                # Fallback: convert to string only if it's a primitive type that makes sense
                elif isinstance(item, (int, float)):
                    cleaned_parts.append(str(item))
            
            final_answer = "".join(cleaned_parts)
        elif not isinstance(final_answer, str):
            # Convert any other type to string
            final_answer = str(final_answer)
        
        # Default response values
        vis_type = "none"
        vis_title = ""
        vis_data = []
        
        # Scan intermediate steps to see if visualization was requested (Fallback for legacy tool usage)
        for action, observation in intermediate_steps:
            # Handle both object (AgentAction) and dict (Cached)
            tool_name = action.tool if hasattr(action, 'tool') else action.get('tool')
            tool_input = action.tool_input if hasattr(action, 'tool_input') else action.get('tool_input')
            
            if tool_name == "create_visualization":
                vis_type = tool_input.get("chart_type", "none")
                vis_title = tool_input.get("title", "")
                
                try:
                    # observation is the return value of create_visualization
                    if isinstance(observation, str):
                        vis_data = json.loads(observation)
                    else:
                        vis_data = observation
                    
                    if isinstance(vis_data, dict) and "image" in vis_data:
                        vis_type = "image"
                        vis_title = vis_data.get("title", vis_title)
                    elif isinstance(vis_data, dict) and "error" in vis_data:
                        print(f"Tool returned error: {vis_data['error']}")
                        final_answer += f"\n\n[System Error: {vis_data['error']}]"
                        vis_data = []
                except Exception as e:
                    print(f"Failed to parse visualization data from intermediate steps: {e}")
                    vis_data = []
                break
        
        # Priority: Check if the LLM outputted a JSON block for visualization
        # This overrides tool usage if present, as it allows for interactive charts
        if "{" in final_answer or "```json" in final_answer:
             try:
                 import re
                 # 1. Try to extract from markdown json block first
                 json_block_match = re.search(r'```json\s*(\{.*?\})\s*```', final_answer, re.DOTALL)
                 potential_json = None
                 match_span = None
                 
                 if json_block_match:
                     potential_json = json_block_match.group(1)
                     match_span = json_block_match.span()
                 else:
                     # 2. Try to find any JSON-like block
                     # We assume the JSON is the *last* structured block or the most prominent one
                     # Regex: Match { ... "visualization_type" ... }
                     # We use a non-greedy dot match inside the braces, but ensure it captures the keys
                     json_match = re.search(r'(\{[\s\S]*?"visualization_type"[\s\S]*?\})', final_answer)
                     
                     if json_match:
                         potential_json = json_match.group(1)
                         match_span = json_match.span()

                 if potential_json:
                     # Attempt to parse
                     try:
                         parsed = json.loads(potential_json)
                     except json.JSONDecodeError:
                         # Retry with loose parsing (sometimes newlines in strings break strict JSON)
                         # Simple cleanup: remove newlines from values if they are not escaped?
                         # Actually usually it's better to just try cleaning the string
                         is_flowchart = "flowchart" in potential_json.lower() or "mermaid" in potential_json.lower()
                         
                         if is_flowchart:
                             # For Flowcharts: Try to extract data field via regex if JSON load failed
                             # patterns to try: "data": "..." or "data": '...'
                             # We use . to match everything including newlines
                             print("Attempting Mermaid Regex Recovery...")
                             import re
                             data_match = re.search(r'"data"\s*:\s*"(.*?)"\s*\}', potential_json, re.DOTALL)
                             if data_match:
                                 # We found the data field at the end
                                 raw_data = data_match.group(1)
                                 # Re-construct a valid object
                                 parsed = {
                                     "visualization_type": "flowchart",
                                     "data": raw_data
                                 }
                             else:
                                 # Fallback to cleaning but warn
                                 cleaned_json = potential_json.replace('\n', ' ').replace('\r', '')
                                 parsed = json.loads(cleaned_json)
                         else:
                             # For Regular Charts: Safe to replace newlines with spaces (usually SQL or metadata)
                             cleaned_json = potential_json.replace('\n', ' ').replace('\r', '')
                             parsed = json.loads(cleaned_json)
                     
                     if "visualization_type" in parsed or "chart_type" in parsed:
                         print("Recovered visualization from text response")
                         vis_type = (parsed.get("visualization_type") or parsed.get("chart_type") or "none").lower()
                         vis_title = parsed.get("visualization_title") or parsed.get("title")
                         vis_data = parsed.get("data")
                         
                         # Execute query if needed (For Interactive Charts)
                         if not vis_data and "data_query" in parsed:
                             print(f"Executing fallback query: {parsed['data_query']}")
                             vis_data_str = execute_sql.invoke(parsed['data_query'])
                             
                             if vis_data_str and not vis_data_str.startswith("Error"):
                                 try:
                                     vis_data = json.loads(vis_data_str)
                                 except Exception as e:
                                     print(f"Failed to load SQL result JSON: {e}")
                                     vis_data = []
                             else:
                                 print(f"SQL Execution failed or returned error: {vis_data_str}")
                                 final_answer += f"\n\n[System Error: {vis_data_str}]"
                                 vis_data = []
                         
                         # Clean the response - remove the entire matched part
                         if match_span:
                            start, end = match_span
                            final_answer = (final_answer[:start] + final_answer[end:]).strip()
             except Exception as e:
                 print(f"Fallback parsing failed: {e}")
               
        # Fallback 2: Check for key-value style (create_visualization query="..." ...)
        if vis_type == "none":
            import re
            # Regex to capture: create_visualization then query="..." chart_type="..." title="..."
            # We use non-greedy matches and allow for newlines
            pattern = r'create_visualization\s+query="(?P<query>.*?)"\s+chart_type="(?P<type>.*?)"\s+title="(?P<title>.*?)"'
            match = re.search(pattern, final_answer, re.DOTALL)
            
            if match:
                print("Recovered visualization from KV-text response")
                q = match.group("query")
                c = match.group("type")
                t = match.group("title")
                
                print(f"Executing fallback visualization (KV): {q}")
                vis_data = generate_plot_image(q, c, t)
                
                if "image" in vis_data:
                    vis_type = "image"
                    vis_title = t
                    final_answer = final_answer.replace(match.group(0), "").strip()
                elif "error" in vis_data:
                    # Provide feedback about the error in the chat
                    final_answer += f"\n\n[System: Visualization failed. Error: {vis_data['error']}]"

        return jsonify({
            "response": final_answer,
            "visualization_type": vis_type,
            "visualization_title": vis_title,
            "data": vis_data
        })

    except Exception as e:
        print(f"Error processing request: {e}")
        return jsonify({"response": "Sorry, I encountered an error while processing your request.", "visualization_type": "none"})


@app.route('/export_to_excel', methods=['POST'])
def export_to_excel():
    try:
        data = request.json
        rows = data.get('rows', [])
        
        if not rows:
            return jsonify({"success": False, "error": "No data to export"})

        # The first row is usually the header
        if len(rows) < 1:
             return jsonify({"success": False, "error": "No data to export"})
             
        # Create DataFrame
        df = pd.DataFrame(rows[1:], columns=rows[0])
        
        # Save to buffer
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Export')
        
        output.seek(0)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"export_{timestamp}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        print(f"Export Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5001)
