'''from langchain.chat_models import ChatOpenAI  # Correct import
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# Step 1: Initialize the LLM for GPT-3.5-Turbo


# Step 4: Define the function
def process_query_to_format(input_query):
    llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0, openai_api_key="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")

    # Step 2: Define the prompt template
    prompt = PromptTemplate(
        input_variables=["input_query"],
        template="""You are an assistant skilled in organizing information into structured formats for presentations.

        Given an input query about creating slides, you should:
        1. Extract the main topics and subtopics.
        2. Determine the number of slides required for each section.
        3. Present the result in the format:
        - Topic 1: X slides
        - Topic 2: Y slides
        - Topic 3: Z slides

        Now, process this query:
        {input_query}"""
    )

    # Step 3: Define the chain
    chain = LLMChain(llm=llm, prompt=prompt)
    # Get the raw output from the LLM
    raw_output = chain.run(input_query)
    print("raw output:" ,raw_output)

    # Step 5: Post-process the output to extract the desired format
    queries_list = []
    for line in raw_output.splitlines():
        if "-" in line and ":" in line:
            try:
                topic, slides_part = line.split(":")
                topic = topic.replace("-", "").strip()
                
                # Extract the numeric value from slides
                slides = ''.join(filter(str.isdigit, slides_part))
                
                if slides.isdigit():  # Ensure it's a valid number
                    slides = int(slides)
                    queries_list.append({"query_text": topic, "num_of_slides": slides})
                else:
                    print(f" Warning: Could not extract slide count from '{slides_part}' in line: {line}")

            except ValueError:
                print(f" Error processing line: {line}")
                continue
            # Extract the topic and number of slides
            #topic, slides = line.split(":")
            #topic = topic.replace("-", "").strip()
            #slides = int(slides.strip().split()[0])  # Extract the number
            #queries_list.append([topic, slides])
            queries_list.append({"query_text":topic,"num_of_slides":slides})
    # Step 6: Deduplicate the list
    unique_queries = []
    seen_topics = set()
        #for topic, slides in queries_list:
        #if topic not in seen_topics:
         #   unique_queries.append([topic, slides])
          #  seen_topics.add(topic)

    for query in queries_list:
        if query["query_text"] not in seen_topics:
            unique_queries.append(query)
            seen_topics.add(query["query_text"])


    # Step 7: Format the output with the word 'queries'
    #return {"queries": unique_queries}  
    print("datatype of output:", type(unique_queries))
    return unique_queries
    
# '''

# from langchain_openai import ChatOpenAI  # Correct import
# from langchain.prompts import PromptTemplate
# from langchain.chains import LLMChain
# import os
# from dotenv import load_dotenv

# load_dotenv()

# openai_api_key = os.getenv("OPENAI_API_KEY")

# # Step 4: Define the function
# def process_query_to_format(input_query):
    
#     # Step 1: Initialize the LLM for GPT-3.5-Turbo
#     llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0, openai_api_key=openai_api_key)

#     # Step 2: Define the prompt template
#     prompt = PromptTemplate(
#     input_variables=["input_query"],
#     template="""You are an assistant skilled in organizing information into structured formats for presentations.

#     Given an input query about creating slides, you should:
#     1. Extract the main topics and subtopics.
#     2. Determine the number of slides required for each section.
#     3. Present the result in the format:
#        - Topic 1: X slides
#        - Topic 2: Y slides
#        - Topic 3: Z slides

#     Now, process this query:
#     {input_query}"""
#     )
    
    
#     # Step 3: Define the chain
#     chain = LLMChain(llm=llm, prompt=prompt)

#     # Get the raw output from the LLM
#     raw_output = chain.run(input_query)
#     print(raw_output)

#     # Step 5: Post-process the output to extract the desired format
#     queries_list = []
#     print("Preparing queries")
#     for line in raw_output.splitlines():
#         if "-" in line and ":" in line:
#             print("line is", line)  # Debugging print

#         # Ensure splitting at first `:` to handle cases with multiple colons
#             topic, slides = line.split(":", 1)  
        
#             topic = topic.replace("-", "").strip()

#         # Extract the first word from slides section
#             slide_words = slides.strip().split()
        
#         # Ensure first word is a digit before conversion
#             if slide_words and slide_words[0].isdigit():
#                slides = int(slide_words[0])
#                queries_list.append({topic: slides})
#             else:
#                 print(f"Skipping line due to non-numeric slide count: {line}")

#     unique_queries = {}
#     for query in queries_list:
#         for topic, slides in query.items():
#             unique_queries[topic] = slides  # Dictionary ensures uniqueness

# # Convert dictionary back to a list of dictionaries
#     unique_queries_list = [{topic: slides} for topic, slides in unique_queries.items()]

#     # Step 7: Format the output with the word 'queries'
#     return unique_queries_list
#     #return queries_list


   
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnableSequence  # NEW import
import os
from dotenv import load_dotenv

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")

def process_query_to_format(input_query):
    # Initialize LLM
    llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0, openai_api_key=openai_api_key)

    # Define prompt
    prompt = PromptTemplate(
        input_variables=["input_query"],
        template="""You are an assistant skilled in organizing information into structured formats for presentations.

        Given an input query about creating slides, you should:
        1. Extract the main topics and subtopics.
        2. Determine the number of slides required for each section.
        3. Present the result in the format:
           - Topic 1: X slides
           - Topic 2: Y slides
           - Topic 3: Z slides

        Now, process this query:
        {input_query}"""
    )

    # ✅ Replace LLMChain with RunnableSequence
    chain = prompt | llm

    # ✅ Replace run() with invoke()
    raw_output = chain.invoke({"input_query": input_query})
    
    print(raw_output.content)  # The response is a ChatMessage object; get `.content`

    queries_list = []
    for line in raw_output.content.splitlines():
        if "-" in line and ":" in line:
            topic, slides = line.split(":", 1)
            topic = topic.replace("-", "").strip()
            slide_words = slides.strip().split()
            if slide_words and slide_words[0].isdigit():
                slides = int(slide_words[0])
                queries_list.append({topic: slides})
            else:
                print(f"Skipping line due to non-numeric slide count: {line}")

    unique_queries = {}
    for query in queries_list:
        for topic, slides in query.items():
            unique_queries[topic] = slides

    unique_queries_list = [{topic: slides} for topic, slides in unique_queries.items()]

    return unique_queries_list


