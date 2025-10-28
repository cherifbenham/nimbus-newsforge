from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig
from utils import MODEL_FLASH
import vertexai
import os


IResponseParams = {
    "ISearchResult": 0,
    "ISearchRequest": 1,
    "ISearchResponse": 2,
}

DE_PROJECT_ID = os.getenv("DISCOVERY_PROJECT_ID") or os.getenv("PROJECT_ID", "fsa-amadeus")
DE_LOCATION = os.getenv("DISCOVERY_LOCATION", "global")
DE_ENGINE_ID = os.getenv("DISCOVERY_ENGINE_ID", "news-finder-v2_1730891472107")

client_options = (
    ClientOptions(api_endpoint=f"{DE_LOCATION}-discoveryengine.googleapis.com")
    if DE_LOCATION != "global"
    else None
)
discovery_client = discoveryengine.SearchServiceClient(
    client_options=client_options)


PROJECT_ID = os.getenv("PROJECT_ID", "fsa-amadeus")
LOCATION = os.getenv("REGION", "us-central1")


vertexai.init(project=PROJECT_ID, location=LOCATION)


def search(
    query: str
) -> discoveryengine.AnswerQueryResponse:

    # The full resource name of the search app serving config
    serving_config = (
        f"projects/{DE_PROJECT_ID}/locations/{DE_LOCATION}/"
        f"collections/default_collection/engines/{DE_ENGINE_ID}/servingConfigs/default_config"
    )

    content_search_spec = discoveryengine.SearchRequest.ContentSearchSpec(
        snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
            return_snippet=True
        ),

        # summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
        #     summary_result_count=10,
        #     include_citations=True,
        #     ignore_adversarial_query=True,
        #     ignore_non_summary_seeking_query=True,
        #     model_prompt_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelPromptSpec(
        #         preamble="You are a News search engine for Amadeus, the travel provider. The returned news are travel industry news"
        #     ),
        #     model_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelSpec(
        #         version="stable",
        #     ),
        # ),
    )

    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=query,
        page_size=10,
        content_search_spec=content_search_spec,
        query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
            condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO,
        ),
        spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
            mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
        ),
    )

    response = discovery_client.search(request)

    formatted_response = []
    for result in response.results:
        struct = dict(result.document.struct_data)
        formatted_response.append(struct)

    prompt = f""" You are a helpful assistant for the competitive intelligence department of Amadeus, the leading travel provider
    Use the following RAG context to answer to the users question.
    Guidelines: if the query is not formulated as a question, try to detect the intent behind the query. Clearly indicate in your response that you reformulated
    Give a markdown formatted result.
    Add citations to the source articles in the form of a hyperlink representing the article url with the label [Read More]
    User question:
    {query}

    RAG context:
    {formatted_response}

    Answer:
    """

    model = GenerativeModel(model_name=MODEL_FLASH)
    responses = model.generate_content(
        [prompt],

    )

    summary = responses.text

    searchResult = {
        "totalsize": response.total_size,
        "summary": summary,
        "results": formatted_response
    }

    return searchResult
