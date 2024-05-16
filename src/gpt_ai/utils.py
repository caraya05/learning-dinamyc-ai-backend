from fastapi import HTTPException
from openai import OpenAI
from config import settings

client = OpenAI(organization=settings.OPENAI_API_ORG_ID,
                api_key=settings.OPENAI_API_KEY,
                # base_url="https://proxy.getprops.ai/",
                # default_headers={"x-api-key": "TFjTs7VL2N4XwPqizdNk"}
                )


def generate_image_dalle(
        prompt: str,
        model: str = "dall-e-3",
        count: int = 1,
        size: str = "1024x1792",
        quality: str = "standard",
):
    try:
        response = client.images.generate(
            model=model,
            prompt=prompt,
            size=size,
            quality=quality,
            n=count,
            style="vivid",
        )

        return response.data[0].url

    except Exception as e:
        print(f"Error DALL-E: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail="The image could not be generated, it probably does not comply with the content policy,"
                   " try to generate it again or contact Qwestar support.",
        )


def generate_gpt4_vision_(
        content_prompt: list[dict], max_tokens: int = 1000, model: str = "gpt-4-vision-preview"
):
    try:
        response = client.chat.completions.create(
            model=model,
            # response_format={"type": "json_object"},
            messages=content_prompt,
            max_tokens=max_tokens,
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"Error GPT4 Vision: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail="Text could not be generated",
        )


def generate_gpt4_(
        content_prompt: list[dict],
        type_text: str = "",
        max_tokens: int = 1000,
        model: str = "gpt-4-turbo",
):
    try:
        response = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=content_prompt,
            max_tokens=max_tokens,
            temperature=0.6,
            # top_p=0.8,
            # frequency_penalty=0.6,
            # presence_penalty=0.7
        )

        # response = client.chat.with_streaming_response.completions.create(
        #     model=model,
        #     response_format={"type": "json_object"},
        #     messages=content_prompt,
        #     max_tokens=max_tokens
        # )
        # print(response.__dict__)

        return response.choices[0].message.content

    except Exception as e:
        print(f"Error GPT4: {str(e)}")
        raise Exception(f"Text not generated {type_text}")


def generate_gpt4o(
        content_prompt: list[dict],
        type_text: str = "",
        max_tokens: int = 1000,
        model: str = "gpt-4o"
):
    try:
        response = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=content_prompt,
            max_tokens=max_tokens,
            temperature=0.6,
            top_p=0.8,
            frequency_penalty=0.6,
            presence_penalty=0.7
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"Error GPT4o: {str(e)}")
        raise Exception(f"Text not generated {type_text}")
