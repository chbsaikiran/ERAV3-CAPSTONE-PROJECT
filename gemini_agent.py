import os
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import date, timedelta

# Load environment variables from .env file
load_dotenv()

# Access your API key and initialize Gemini client correctly
api_key = os.getenv("GEMINI_API_KEY")
#client = genai.Client(api_key=api_key)
genai.configure(api_key=api_key)

def get_details_from_email_body(email_body,user_query):
    model = genai.GenerativeModel("gemini-2.0-flash")
    final_prompt = f"""Your task is to extract the following details from the email body based on the user's query:
    {user_query}
1. Amounts: Look for monetary amounts in various formats (e.g., ₹123,
    Rs. 456, $789.00, etc.) and list them.
2. Dates: Identify any dates mentioned in the email body in various formats
    (e.g., DD/MM/YYYY, MM-DD-YYYY, Month Day, Year, etc.) and list them.
3. Keywords: Extract keywords related to expenses, orders, transactions,
    bookings, payments, refunds, cancellation etc. List all relevant keywords found in the email body.
4. Summary: Provide a brief summary of the email content in one or two sentences. and definetely include the of from where to where the journey happened in case of travel bookings
5. If the amounts in not in float or integer format then ignore that amount
6. If no details found then return None for that field
Only provide the extracted information in a structured format as shown below.
If any of the details are not found, indicate "None" for that field.
Format:
Amounts: [list of amounts or "None"]
Dates: [list of dates or "None"]
Keywords: [list of keywords or "None"]
Summary: [brief summary or "None"]
Email Body: {email_body}
Extracted Details:"""
    response = model.generate_content(final_prompt)
    return response.text.strip().strip('"')

def build_gmail_search_query(natural_question: str) -> str:
    today = date.today()
    year = today.year
    month = today.month
    day = today.day

    # Also useful to precompute yesterday, last_week etc. for examples
    yesterday = today - timedelta(days=1)
    last_week = today - timedelta(days=7)
    last_month = today - timedelta(days=30)
    last_ten_years = today - timedelta(days=3650)

    model = genai.GenerativeModel("gemini-2.0-flash")
    system_prompt = f"""
You are an AI expert at writing Gmail search queries.
Convert the following user question into a Gmail search query syntax.
Only output the Gmail query string. Do not explain anything.

Today's date is {today} (Year={year}, Month={month}, Day={day}).
Yesterday is {yesterday}.
One week ago was {last_week}.
Examples to identify main keywords
if user asks "Zomato orders this year" main keyword is "Zomato"
if user asks "IRCTC last week" main keyword is "IRCTC"
if user asks "where did I travel using Redbus in last one month" main keyword is "Redbus"
if user asks "OTP from SBI yesterday" main keyword is "OTP" and SBI"
if user asks "which books did I buy on amazon this year??" main keywords are "books" , "amazon"
if user asks "when did I buy Atomic Habits by James Clear on Amazon" main keywords are "Atomic Habits", "James Clear" , "Amazon"
if user asks "when did I buy iphone 13 on Croma this year??" main keywords are "iphone 13" "Croma"
if user asks "when did I buy Samsung Mobile on Flipkart" main keywords are "Samsung" "Flipkart"
So multiple main keywords can be there in the User Query search query and find all the main keywords and put them in quotes and return it as output query

IMPORTANT RULES:
1. Include the all days in date ranges
2. Never skip any days in the range
3. You have pick the keywords from the User Query and do spelling corrections, identify all the main keywords and put them in quotes and return it as output query
4. Always use after: and before: for date ranges
5. only include INR currency transactions only, don't include any other currency transactions. This is most important rule

Examples:
if user asks "Zomato orders this year" return:
'"Zomato" INR after:{year}/01/01 and before:{today}'

if user asks "IRCTC last week" return:
'"IRCTC" INR after:{last_week} and before:{today}'

if user asks "where did I travel using Redbus in last one month" return:
'"Redbus" INR booking after:{last_month} and before:{today}'

if user asks "OTP from SBI yesterday" return:
'"OTP" "SBI" after:{yesterday} and before:{today}'

example with two keywords in User Query "which books did I buy on amazon this year??" return:
'"books" "amazon" after:{year}/01/01 and before:{today}'

For queries where the date is not mentioned search the mails for last 10 years i.e. if user asks "when did I buy Atomic Habits by James Clear on Amazon" return:
'"Atomic Habits", "James Clear" "Amazon" after:{last_ten_years} and before:{today}'

Below are examples of how to handle specific user queries:
when did I buy iphone 13 on Croma this year?? return:
'"iphone 13" "Croma" after:{year}/01/01 and before:{today}'

How much did I pay for coursera subscription using axis bank in this year??: return:
'"coursera" "axis bank" after:{year}/01/01 and before:{today}'

For queries where the date is not mentioned search the mails for last 10 years
 i.e. if user asks "when did I buy Samsung Mobile on Flipkart" return:
'"Samsung" "Flipkart" after:{last_ten_years} and before:{today}'

User Query:
{natural_question}
"""
    response = model.generate_content(system_prompt)
    return response.text.strip().strip('"')

def summarize_emails_with_query(user_query: str, snippets: list[str]) -> str:
    model = genai.GenerativeModel("gemini-2.0-flash")
    combined_emails = "\n\n".join(snippets[:50])  # Increased to match max_results
    final_prompt = f"""
You are an assistant who analyzes Gmail content and answers user queries accurately.
Your task is to:
1. Understand the specific question being asked
2. Analyze the email snippets to find relevant information
3. Provide a clear, concise answer that directly addresses the user's query
4. When analyzing expenses or orders on online shopping platforms like Amazon, Flipkart, etc:
   - Include ALL transactions from the entire date range, but only show each transaction with its date, item purchased and amount spent on that particular order
   - Maintain chronological order
5. When analyzing expenses or orders on online food delivery platforms like Zomato, Swiggy, etc:
   - Include ALL transactions from the entire date range, but only show each transaction with its date, restaurant name, item ordered and amount spent on that particuar order
   - Maintain chronological order
   - Don't Calculate the total amount leave it as Total Amount Spent is : TO BE ADDED LATER, I will later replace the "TO BE ADDED LATER" with correct total amount later.
6. If the query is about travel or bookings:
   - Most impotrtant include the journey details like from where to where the journey happened
   - if in summary if the ticket was cancelled include that information in the answer that ticket is cancelled mention that ticket cancelled in the answer
   - Focus on the specific information requested
   - Provide relevant details from the emails like date, location and amount spent on ticket in the case of travel or amount spent on booking in case of bookings.
   - Maintain chronological order
   - Don't Calculate the Total amount leave it as "Total Amount Spent is : TO BE ADDED LATER", I will later replace the "TO BE ADDED LATER" with correct total amount.
7.  If the query is about expenses or orders:
   -  Don't Calculate the Total amount leave it as "Total Amount Spent is : TO BE ADDED LATER", I will later replace the "TO BE ADDED LATER" with correct total amount.
8. If any other user query Answer the question based on the email snippets, focusing specifically on what was asked.
9. If there are no relevant emails, respond with "No relevant information found in the emails."
10. If the query says summarize then summarize each email briefly in one or two sentences.
EMAIL SNIPPETS:
{combined_emails}

USER QUESTION:
{user_query}
"""
    response = model.generate_content(final_prompt)
    #print(response.text)
    return response.text

def get_total_expenses_from_emails_with_query(summarized_answer: str) -> str:
    model = genai.GenerativeModel("gemini-2.0-flash")
    final_prompt = f"""
You are an assistant who analyzes summarized answer to a gmail query, and sees if there are expenses or amount spent in the summarized answer if the answer is yes then:
From ALL these transactions, just give all expenses separated by | and with prefix FUNCTION_CALL: add_list . Don't give any other output, only the expenses separated by | and with prefix FUNCTION_CALL: add_list .
if the summary has amounts like this below(the actual data may look different) but your task is to separate out the amounts for each transaction.
    Eg: Zomato order of amount on 29th March 2025 is Rs 250.50
    Zomato order of amount on 7th April 2025 is Rs 260.50
    Zomato order of amount on 9th May 2025 is Rs 1500.60
    Then you should give result as "FUNCTION_CALL: add_list|250.50|260.50|1500.60" without quotes and nothing else needs to be output
    if they are no expenses in the summary then just output "FUNCTION_CALL: add_list|0" without quotes and nothing else needs to be output

Summarized answer to gmail query:
{summarized_answer}
"""
    response = model.generate_content(final_prompt)
    return response.text

def Replace_total_expenses_from_emails_with_query(summarized_answer: str, Total_Expenses: str) -> str:
    model = genai.GenerativeModel("gemini-2.0-flash")
    final_prompt = f"""
You are an assistant who analyzes summarized answer to a gmail query, and your job is to fill in the text "Total Amount Spent is : TO BE ADDED LATER" in the place of TO BE ADDED LATER put {Total_Expenses}, remaining all text remains the same, don't change anything else.
Eg: if the input looks like this(actual may differ) but your task is to only replace TO BE ADDED LATER with {Total_Expenses}
    Zomato order amount on 29th March 2025 is Rs 250.50
    Zomato order amount on 7th April 2025 is Rs 260.50
    Zomato order amount on 9th May 2025 is Rs 1500.60
    Total Amount Spent is : TO BE ADDED LATER

   You need to output:
    Zomato order amount on 29th March 2025 is Rs 250.50
    Zomato order amount on 7th April 2025 is Rs 260.50
    Zomato order amount on 9th May 2025 is Rs 1500.60
    Total Amount Spent is : {Total_Expenses}

Summarized answer to gmail query:
{summarized_answer}
"""
    response = model.generate_content(final_prompt)
    return response.text
