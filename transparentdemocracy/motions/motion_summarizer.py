from openai import OpenAI

class MotionSummarizer:
    def __init__(self):
        self.client = OpenAI()
        self.model = "gpt-3.5-turbo"

    def summarize(self, motion_description):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a motion summarizer. You respond with a short summary of each "
                                              "motion you receive from the user."},
                {"role": "user", "content": motion_description},
            ],
        )
        return response.choices[0].message.content