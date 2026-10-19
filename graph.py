from langgraph.graph import StateGraph, START, END
from agents.intake_agent import get_profile
from state import UserProfile

CASTE_OPTIONS = ["OC", "BC", "SC", "ST", "EWS", "Minority"]


def clean_caste(value):
    if not value:
        return None
    value = str(value).strip()
    for option in CASTE_OPTIONS:
        if value.lower() == option.lower():
            return option
    return None


def intake_node(state: UserProfile) -> UserProfile:
    """Takes the user details with the help of a Voice agent"""

    profile_data = get_profile()

    if profile_data is None:          # user quit before confirming
        print("Intake was not completed. The profile is unchanged.")
        return state

    return UserProfile(
        age=profile_data.get("age"),
        gender=profile_data.get("gender"),
        state=state.state,            # keeps "Andhra Pradesh"
        district=profile_data.get("district"),
        occupation=profile_data.get("occupation"),
        annual_income=profile_data.get("annual_income"),
        land_acres=profile_data.get("land_acres"),
        caste_category=clean_caste(profile_data.get("caste_category")),
    )


graph = StateGraph(UserProfile)
graph.add_node("intake", intake_node)
graph.add_edge(START, "intake")
graph.add_edge("intake", END)
app = graph.compile()

result = app.invoke(UserProfile())
print(result)