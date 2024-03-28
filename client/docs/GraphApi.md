# template_web_client.GraphApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**update_graph_api_v0_graph_patch**](GraphApi.md#update_graph_api_v0_graph_patch) | **PATCH** /api/v0/graph | Update Graph


# **update_graph_api_v0_graph_patch**
> str update_graph_api_v0_graph_patch()

Update Graph

Update Distributed Knowledge Graph

### Example


```python
import template_web_client
from template_web_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = template_web_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with template_web_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = template_web_client.GraphApi(api_client)

    try:
        # Update Graph
        api_response = api_instance.update_graph_api_v0_graph_patch()
        print("The response of GraphApi->update_graph_api_v0_graph_patch:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling GraphApi->update_graph_api_v0_graph_patch: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**str**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

