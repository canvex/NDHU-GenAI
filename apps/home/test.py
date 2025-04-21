# import the inference-sdk
from inference_sdk import InferenceHTTPClient

# initialize the client
CLIENT = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key="hDeBVe4jSauWQ2OrRlvQ"
)

# infer on a local image
result = CLIENT.infer("/Users/annietsai/downloads/trains_forms/t1.pdf", model_id="my-first-project-ksnki/5")
print(result).json()