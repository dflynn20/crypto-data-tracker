import os

def validateAuthorization(request):
    return 'Authorization' in request.headers and os.environ.get("AUTHORIZATION_TOKEN") == request.headers['Authorization']


# Makes sure that the necessary parameters are passed from the frontend, properly throws which fields were not specified.
def checkParams(data):
    params = data.keys()
    errorMessage = ""
    for key in ["userId","market","pair","metric"]:
        if key not in params:
            if len(errorMessage) == 0:
                errorMessage = f"Missing {key}"
            else:
                errorMessage += f", {key}"
    if len(errorMessage) > 0:
        errorMessage += " this must be specified in order to add this metric."
        return errorMessage, None, None, None, None
    return "", data["userId"], data["market"], data["pair"], data["metric"]
