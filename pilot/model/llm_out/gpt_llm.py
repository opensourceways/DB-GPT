import json
import os
import openai

openai.api_key = os.getenv("OPENAI_KEY", None)

messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Who won the world series in 2020?"},
        {"role": "assistant", "content": "The Los Angeles Dodgers won the World Series in 2020."},
        {"role": "user", "content": "Where was it played?"}
    ]


def chat_gpt(question, model="gpt-3.5-turbo", stream=False):
    message = {"role": "user", "content": question}
    messages = [message]
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        stream=stream
    )
    response = response['choices'][0]['message']['content']
    return response


def chat_gpt_stream(question, model="gpt-3.5-turbo", stream=True):
    message = {"role": "user", "content": question}
    messages = [message]
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        stream=stream
    )
    for chunk in response:
        content = ''
        if "content" in chunk["choices"][0]["delta"]:
            content = chunk["choices"][0]["delta"]["content"]
            data = json.dumps({"answer": content}, ensure_ascii=False)
            yield f"data: {data}\n"