# Kiểm tra kết nối tới Open AI ( xem đã kết nối được tới model cần sử dụng chưa : thử hỏi xem model có trloi ko ) 
from pydantic import BaseModel

from openai_config import make_openai_llm


class CheckResult(BaseModel):
    answer: str


def main() -> None:
    llm = make_openai_llm()
    result = llm.with_structured_output(CheckResult).invoke("Return the word 'ok' as the answer.")
    if not result or not result.answer.strip():
        raise ValueError("OpenAI returned an empty structured answer")
    print(f"OpenAI structured-output check succeeded using {llm.model_name}")


if __name__ == "__main__":
    main()
