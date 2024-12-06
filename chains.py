from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field

from dotenv import load_dotenv

load_dotenv()

#####################
#### ENRICHMENT #####
#####################

class EnrichedQuery(BaseModel):
    enriched_query: str = Field(description="this is the enriched query")

# Set up a parser + inject instructions into the prompt template.
parser = JsonOutputParser(pydantic_object=EnrichedQuery)

normalize_prompt = PromptTemplate(
    template="You role is to enrich the provided user query about fitness to make sure it's clear.\n{format_instructions}\n{query}\n",
    input_variables=["query"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)

enrich_chain = (
    normalize_prompt
    | ChatOpenAI(model="gpt-4o", temperature=0)
    | parser
)

    
###################
##### ROUTING #####
###################
routing_chain = (
    PromptTemplate.from_template(
        """Given the user question below, you need to decide where to route it. These are the possible routes:

    - WorkoutPlan: Generate a weekly workout planusing exercises in the database.
    - ExerciseInfo: Provide information about specific exercises in the database.
    - NotSupported: Any other request.

Just respond with one word, the name of the route you selected.

<question>
{question}
</question>

Classification:"""
    )
    | ChatOpenAI(model="gpt-4o", temperature=0)
    | StrOutputParser()
)


########################
##### WORKOUT PLAN #####
########################
workout_plan_prompt = PromptTemplate(
    template="""
    You are a personal trainer. Your task is to create personalized workout plans for users based on their requests.

    User profile:
    {user_profile}

    User query: {query}

    Use the following exercises for the plan. You don't necessarily have to use all of them, but you can only choose from this list:
    {exercises}

    The output must be in the following JSON format, rest days simply have an empty array:
    {{
        "type": "workout_plan",
        "plan": [
            {{"day": "Monday", "exercises": [
                {{"exercise_id": 1, "sets": "3", "repetitions": "10"}},
                {{"exercise_id": 2, "sets": "3", "repetitions": "15"}}
            ]}},
            {{"day": "Tuesday", "exercises": []}},
            {{"day": "Wednesday", "exercises": [
                {{"exercise_id": 3, "sets": "4", "repetitions": "12"}},
                {{"exercise_id": 4, "sets": "3", "repetitions": "10"}}
            ]}}
            ...
        ]
    }}
    """,
    input_variables=["user_profile", "query", "exercises"]
)

workout_plan_chain = (
    workout_plan_prompt
    | ChatOpenAI(model="gpt-4o", temperature=0)
    | JsonOutputParser()
)

########################
##### SUMMARY #####
########################
summary_prompt = PromptTemplate(
    template="""
    You are a personal trainer. Your task is to provide a user with a short paragrpah to complement the provided workout plan. The plan is in JSON format, with all the exercises to perform each day. Empty days are just for rest.

    User profile:
    {user_profile}

    Workout plan:
    {workout_plan}
    
    Just respond with the paragraph for the user, remember they can see the plan so you want to provide short tailored advice and information to complement the plan, do not regurgitate the plan to them.
    """,
    input_variables=["user_profile", "workout_plan"]
)


summary_chain = (
    summary_prompt
    | ChatOpenAI(model="gpt-4o", temperature=0)
    | StrOutputParser()
)


#########################
##### EXERCISE INFO #####
#########################

exercise_info_prompt = PromptTemplate(
    template="""
    You are a personal trainer. Your task is to provide the user with a list of exercises that match their query.

    User query: {query}

    Choose from the following list of exercises an appropriate subset that matches the user's query:
    {exercises}

    The output must be in the following JSON format, containing an array of just exercise IDs, nothing else:
    {{
        "type": "exercises",
        "exercise_ids": [1,15,20]
    }}
    """,
    input_variables=["query", "exercises"]
)

exercise_info_chain = (
    exercise_info_prompt
    | ChatOpenAI(model="gpt-4o", temperature=0)
    | JsonOutputParser()
)

