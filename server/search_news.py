def search_news(
    project_id: str,
    location: str,
    engine_id: str,
    search_query: str,
) -> List[discoveryengine.SearchResponse]:
    client_options = (
        ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
        if location != "global"
        else None
    )

    client = discoveryengine.SearchServiceClient(client_options=client_options)

    serving_config = f"projects/{project_id}/locations/{location}/collections/default_collection/engines/{engine_id}/servingConfigs/default_config"

    content_search_spec = discoveryengine.SearchRequest.ContentSearchSpec(
        snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
            return_snippet=True
        ),
        summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
            summary_result_count=5,
            include_citations=True,
            ignore_adversarial_query=True,
            ignore_non_summary_seeking_query=True,
            model_prompt_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelPromptSpec(
                preamble="YOUR_CUSTOM_PROMPT"
            ),
            model_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelSpec(
                version="stable",
            ),
        ),
    )

    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=search_query,
        page_size=5,
        content_search_spec=content_search_spec,
        query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
            condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO,
        ),
        spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
            mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
        ),
    )

    response = client.search(request)

    return response

def extract_results(response):
    formatted_response = {}
    articles = []

    results = response.results
    for idx, result in enumerate(results):
        article = {}
        for key, value in result.document.struct_data.items():
            article[key] = value
        derived_struct_data = recurse_proto_marshal_to_dict(result.document.derived_struct_data)
        if derived_struct_data['snippets']['snippet_status'] == 'SUCCESS':
            article['snippet'] = derived_struct_data['snippets']['snippet']
        articles.append(article)

    formatted_response['articles'] = articles

    if response.summary.summary_with_metadata.summary:
        formatted_response['summary'] = response.summary.summary_with_metadata.summary

    return formatted_response

def recurse_proto_marshal_to_dict(object):
    new_dict = {}
    for k, v in object.items():
      if not v:
        continue
      elif isinstance(v[0], maps.MapComposite):
          v = recurse_proto_marshal_to_dict(v[0])
      new_dict[k] = v

    return new_dict 
