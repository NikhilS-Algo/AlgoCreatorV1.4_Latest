from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from prompts import AGENT_PROMPT
from tools import toolkit
import json # Import json for handling tool output

def run_agent(query, chat_history):
    """
    Executes the ReAct agent to process a user query while maintaining conversation history.

    :param query: The user's query as a string.
    :param chat_history: A list of past messages to maintain user-specific context.
    :return: The final content of the response from the agent or a fallback message.
    """

    try:
        print("Query received by run_agent:", query)

        sys_prompt = AGENT_PROMPT
        llm = load_llm_model()
        agent_executor = create_react_agent(llm, toolkit)

        past_messages = []
        for msg in chat_history:
            if msg["sender"] == "user":
                past_messages.append(HumanMessage(content=msg["message"]))
            elif msg["sender"] == "bot":
                past_messages.append(AIMessage(content=msg["message"]))

        truncated_history = past_messages[-10:]

        messages = [SystemMessage(content=sys_prompt)] + truncated_history + [HumanMessage(content=query)]

        response = agent_executor.invoke({"messages": messages})

        # Process the final content from the agent's response
        final_content_message = response.get("messages", [])[-1]
        final_content = final_content_message.content if final_content_message else None

        print("------------------------------------------------")
        print(response)
        print("--------------------------------------------------")
        print("Final content extracted:", final_content)

        # Enhanced handling of tool output for user display
        if final_content_message.type == "tool_output":
            try:
                tool_output_dict = final_content_message.content
                if isinstance(tool_output_dict, str): # Handle cases where tool output might be a stringified dict
                     tool_output_dict = json.loads(tool_output_dict)

                if "pdf_url" in tool_output_dict and tool_output_dict["pdf_url"]:
                    pdf_url = tool_output_dict["pdf_url"]
                    slide_metadata = tool_output_dict.get("slide_metadata", [])
                    num_slides = len(slide_metadata)
                    
                    # Construct a user-friendly message
                    if num_slides > 0:
                        slide_summaries = "\n".join([
                            f"- Slide {s.get('slide_number', 'N/A')} from '{s.get('ppt_name', 'N/A')}' (Topic: {s.get('topic', 'N/A')}): {s.get('slide_summary', '')[:100]}..." # Truncate summary
                            for s in slide_metadata[:3] # Show details for first few slides
                        ])
                        return (
                            f"✅ I've successfully retrieved {num_slides} slides and generated a PDF! "
                            f"You can download it here: [Retrieved Slides PDF]({pdf_url})\n\n"
                            f"Here's a glimpse of the retrieved content:\n{slide_summaries}\n\n"
                            "Would you like to refine the search or explore similar topics?"
                        )
                    else:
                        return f"ℹ️ I couldn't find any slides matching your request. The PDF link is: [Empty PDF]({pdf_url}). Would you like to try a different query?"
                elif "error" in tool_output_dict:
                    return f"❌ An error occurred during retrieval: {tool_output_dict['error']}. Details: {tool_output_dict.get('details', 'No additional details.')} Please try again or refine your query."
                elif "message" in tool_output_dict and "saved successfully" in tool_output_dict["message"]:
                    return tool_output_dict["message"] # Pass through success message for saving JSON
                else:
                    return f"I performed an action. Here's the raw output: {final_content}"
            except json.JSONDecodeError:
                return f"I performed an action. Here's the raw output (non-JSON): {final_content}"
            except Exception as tool_e:
                print(f"Error processing tool output: {tool_e}")
                return f"I performed an action, but there was an error processing the result: {final_content}"

        return final_content or "Sorry, I couldn't process your query."
    except Exception as e:
        print(f"Unexpected error in run_agent: {e}")
        return "An unexpected error occurred. Please try again later."

# def load_llm_model():
#     """
#     Loads the LLM model from environment variables.

#     Returns:
#         ChatOpenAI: The loaded model.
#     """
#     from langchain_openai import ChatOpenAI
#     import os
#     from dotenv import load_dotenv

#     try:
#         load_dotenv()
#         return ChatOpenAI(
#             model="gpt-4o-mini",  
#             temperature=0.1,
#             openai_api_key=os.getenv("OPENAI_API_KEY")
#         )
#     except KeyError as e:
#         print(f"Missing environment variable: {e}")
#         raise RuntimeError("One or more environment variables are not set. Please check the .env file.") from e
#     except Exception as e:
#         print(f"Error loading LLM model: {e}")
#         raise RuntimeError("An error occurred while loading the LLM model.") from e

def load_llm_model():
    """
    Loads the Gemini LLM model from environment variables.

    Returns:
        ChatGoogleGenerativeAI: The loaded model.
    """
    # 1. New import for Gemini model in LangChain
    from langchain_google_genai import ChatGoogleGenerativeAI
    import os
    from dotenv import load_dotenv

    try:
        load_dotenv()
        
        # Check for the Google API key specifically
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
             # Fallback to the standard name if user used it
             api_key = os.getenv("GOOGLE_API_KEY")

        if not api_key:
            raise KeyError("GEMINI_API_KEY or GOOGLE_API_KEY")

        # 2. Use ChatGoogleGenerativeAI instead of ChatOpenAI
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", # A suitable, fast model similar to gpt-4o-mini
            temperature=0.1,
            # The API key is passed here. LangChain handles the authentication.
            google_api_key=api_key 
        )
    except KeyError as e:
        print(f"Missing environment variable: {e}")
        # Updated instructions to reflect the new key requirement
        raise RuntimeError("The GEMINI_API_KEY (or GOOGLE_API_KEY) environment variable is not set. Please check your .env file.") from e
    except Exception as e:
        print(f"Error loading LLM model: {e}")
        raise RuntimeError("An error occurred while loading the LLM model.") from e