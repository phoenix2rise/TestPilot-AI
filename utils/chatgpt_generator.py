import openai

def generate_test_script(prompt):
    openai.api_key = "YOUR_OPENAI_KEY"

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a test automation expert."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    prompt = input("Enter test scenario: ")
    script = generate_test_script(prompt)
    print("\nGenerated Test Code:\n")
    print(script)
