"""
file này đang cải tiến chất lượng testset được sinh ra bởi Ragas bằng cách tối ưu, đưa nhiều thông tin hướng dẫn hơn 
vào Prompt (đưa cho LLM) để sinh ra testset. Bao gồm : 
1.Dùng KeyphrasesExtractor để trích keyphrase từ chunk.
2.Cấu hình synthesizer dùng keyphrase làm chủ đề câu hỏi.
3.Cố định persona nhân viên, phong cách ngữ pháp chuẩn và độ dài trung bình.
"""
import asyncio
import argparse
import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("RAGAS_DO_NOT_TRACK", "true")

from langchain_community.callbacks.manager import get_openai_callback
from ragas.run_config import RunConfig
from ragas.testset.persona import Persona
from ragas.testset.synthesizers import SingleHopSpecificQuerySynthesizer
from ragas.testset.synthesizers.base import QueryLength, QueryStyle
from ragas.testset.synthesizers.single_hop.prompts import (
    GeneratedQueryAnswer, QueryAnswerGenerationPrompt, QueryCondition,
)
from ragas.testset.transforms import KeyphrasesExtractor
# ragas hỗ trợ sẵn công cụ thể trích được ra Key Phrase 

from generate_pilot import load_source_chunks
from openai_config import make_testset_generator

OUTPUT_DIR = Path(__file__).resolve().parent / "pilot_v2"
SELECTION = [
    ("Ask Me Anything", 1),
    ("Ask Me Anything", 2),
    ("Ask Me Anything", 3),
    ("GitLab Internal Acceptable Use Policy", 8),
    ("GitLab Internal Acceptable Use Policy", 13),
    ("GitLab Internal Acceptable Use Policy", 20),
    ("Global Travel and Expense Policy", 6),
    ("Global Travel and Expense Policy", 11),
    ("Global Travel and Expense Policy", 27),
    ("The complete guide to remote onboarding for new-hires", 7),
    ("The complete guide to remote onboarding for new-hires", 8),
    ("The complete guide to remote onboarding for new-hires", 18),
    ("Leave Types", 9),
    ("Leave Types", 6),
    ("Leave Types", 12),
    # Chọn ra 15 chunks từ 3 Documents 
]
INSTRUCTION = """Generate one useful, self-contained English employee question and a reference answer.
Use the supplied context as evidence. The selected keyphrase MUST be the primary
subject of the question: ask about a specific stated fact or rule concerning it,
not an unrelated action elsewhere in the context. Do not invent a role,
platform, rule or relationship just to use a word.
Ask about one concrete action, requirement, exception, permission or condition an
employee might need to know. Name the specific object (e.g. an integration, not
the entire product). Avoid vague questions such as 'What is the role of GitLab?'
and 'What does GitLab have to do with ...?'. Use natural, grammatical English,
not slang, deliberate misspellings, or a list of keywords. Prefer a focused
question over 'What are all the best practices?'.
Before returning the pair, verify each answer claim against the exact context
and correct any changed modality or missing exception. The answer must directly answer the question using only explicit information
in the context. Preserve EVERY relevant qualifier: if, may, should, must, only,
unless, exceptions, actor and approval authority. Conditional contact or approval
must not become guaranteed. Recommendations must not become obligations.
Do not invent details behind links. Keep the answer concise (usually 1-3 sentences)
and omit unrelated policy points. Make different keyphrases lead to different
information needs, not superficial paraphrases of the same question.
"""
# Ta hiểu thế này, cuối cùng thì vẫn là LLM tạo ra bộ testset. Mà LLM chỉ làm việc với
# text, vì vậy, ta có thể thêm quy tắc này vào đoạn text, để LLM có thể gen ra testset đúng theo mong muốn :
# Các yêu cầu bao gồm : 
"""
Tập trung đúng trọng tâm (Keyphrase-centric): Câu hỏi phải xoay quanh trực tiếp từ khóa được chọn và chỉ đích danh đối tượng cụ thể (hành động, điều kiện, ngoại lệ...), tuyệt đối tránh hỏi chung chung, mơ hồ.

Trung thực tuyệt đối với ngữ cảnh (Strict Grounding): Chỉ dùng thông tin có sẵn trong văn bản, không suy diễn nội dung đằng sau các đường link hay tự bịa thêm vai trò/quy định.

Bảo toàn sắc thái và điều kiện (Modality & Constraints Preservation): Phải đối chiếu lại câu trả lời để giữ nguyên mức độ ràng buộc (nên khác phải, có điều kiện khác chắc chắn) cùng mọi ngoại lệ và thẩm quyền phê duyệt.

Ngắn gọn và đa dạng (Concise & Distinct): Câu trả lời gói gọn trong 1–3 câu tiếng Anh chuẩn mực, đi thẳng vào vấn đề; các từ khóa khác nhau phải khai thác các khía cạnh thông tin khác nhau thay vì lặp lại ý.

""" 

class FocusedSingleHop(SingleHopSpecificQuerySynthesizer):    
    # Tự tạo ra Synthesizer để có thể chỉnh sửa các tham số cấu hình theo ý muốn 
    # Vai trò của Synthesizer : chính là thành phần trực tiếp tạo ra câu prompt để đưa vào LLM để LLM generate testset 

    # Synthesizer nhận vào các tham số, các tham số này dùng để tạo scenario (dạng như context quy định LLM cách làm việc)
    def prepare_combinations(self, node, terms, personas, persona_concepts):
        combinations = super().prepare_combinations(node, terms, personas, persona_concepts)
        for combination in combinations:
            combination["styles"] = [QueryStyle.PERFECT_GRAMMAR]
            combination["lengths"] = [QueryLength.MEDIUM]
        return combinations


def focused_prompt():
    prompt = QueryAnswerGenerationPrompt() 
    # Tại sao lại dùng QA Generation Prompt,nó có sẵn nhx nội dung j, nó có phải là cái dùng để Tạo testset : Querry, Relavant chunks hay không
    prompt.instruction = INSTRUCTION
    # Phần example này chính là 1 ví dụ few shot learning
    prompt.examples = [(
        QueryCondition(
            persona=Persona(name="Employee", role_description="Needs practical workplace guidance."),
            term="additional clarification", query_style="PERFECT_GRAMMAR", query_length="MEDIUM",
            context="The review team may ask an applicant for additional clarification if the submitted evidence is insufficient. Otherwise it assesses the existing evidence.",
        ),
        GeneratedQueryAnswer(
            query="When might the review team ask an applicant for additional clarification?",
            answer="The review team may ask for clarification if the submitted evidence is insufficient.",
        ),
    )]
    return prompt
# Xây dựng prompt để generate SingleHop testset 


def map_sources(rows, documents):
    """Attach actual Qdrant identifiers; reject unsupported provenance."""
    mapped = []
    for i, row in enumerate(rows, 1):
        if not row.get("user_input", "").strip() or not row.get("reference", "").strip():
            raise ValueError(f"Case {i} has an empty question or reference")
        contexts = row.get("reference_contexts", [])
        matches = [d for d in documents if d.page_content in contexts]
        if len(matches) != 1 or len(contexts) != 1:
            raise ValueError(f"Case {i} has ambiguous or missing source provenance")
        metadata = matches[0].metadata
        mapped.append({**row, "id": f"v2-{i:02d}",
                       "reference_document_ids": [metadata["document_id"]],
                       "reference_context_ids": [metadata["chunk_id"]],
                       "source_title": metadata["title"], "section_path": metadata["section_path"],
                       "review_status": "pending", "human_approved": False})
    return mapped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    output_dir = parser.parse_args().output_dir.resolve()
    output_dir.mkdir(exist_ok=True, parents=True)
    if any((output_dir / name).exists() for name in ("testset_raw.json", "usage.json")):
        raise FileExistsError("Preserve the existing pilot_v2 run before rerunning")
    random.seed(42)
    generator = make_testset_generator()
    # gắn thêm trường mặc định cho Generator : Persona : Auto là Employee
    generator.persona_list = [Persona(name="Employee", role_description="A GitLab team member seeking practical guidance on workplace policies, events, onboarding and leave.")]
    documents = load_source_chunks(SELECTION)
    (output_dir / "sources.json").write_text(json.dumps(
        [{"metadata": d.metadata, "text": d.page_content} for d in documents],
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    synthesizer = FocusedSingleHop(llm=generator.llm, property_name="keyphrases",
                                  generate_query_reference_prompt=focused_prompt())
    # Synthesizer là thành phần trực tiếp kết nối tới LLM, tạo prompt để LLM gentest
    # Vì vậy ta cần truyền vào LLM, ngoài ra còn truyền vào prompt sẵn, và property cần thiết để bổ sung scenario
    """
     * giải thích 2 tham số : 

    """
    started = datetime.now(timezone.utc)
    with get_openai_callback() as usage:
        try:
            # Phần gọi hàm Generator: 
            async def generate():
                return generator.generate_with_langchain_docs(
                    documents, testset_size=15, 
                    transforms=[KeyphrasesExtractor(llm=generator.llm, max_num=3)],
                    # Transform là danh sách các bước xử lý tài liệu trước khi sinh ra câu hỏi 
                    # Ở đây nó đang sử dụng LLM để trích xuất ra các Từ khóa Keyphrase, sau đó Keyphrase này được lưu lại trong Knowledge Graph của Generator và dược Synthesizer dùng để làm chủ đề tạo câu hỏi
                    query_distribution=[(synthesizer, 1.0)],
                    # Các đối tượng Synthesizer này thực chất chính là những mẫu prompt khác nhau 
                    # ở đây ta tự định nghĩa FocusedSingleHop kế thừa từ singlehop, sau đó ta sửa lại đoạn Prompt để theo đúng tác vụ mình mong muốn 
                    run_config=RunConfig(max_workers=2, timeout=180), raise_exceptions=True,
                )
            rows = map_sources(asyncio.run(generate()).to_list(), documents)
            if len(rows) != 15:
                raise ValueError(f"Expected 15 cases, received {len(rows)}")
            (output_dir / "testset_raw.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Generated {len(rows)} source-mapped cases in {output_dir}")
        finally:
            stats = {
                "started_at_utc": started.isoformat(), "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                "openai_model": os.getenv("OPENAI_EVAL_MODEL", "gpt-4o-mini"),
                "openai_successful_requests": usage.successful_requests,
                "openai_input_tokens": usage.prompt_tokens, "openai_output_tokens": usage.completion_tokens,
                "openai_cost_usd_callback_estimate": usage.total_cost,
                "voyage_requests": 0,
                "source_chunk_count": len(documents),
                "prompt_instruction": INSTRUCTION,
                "source_selection": SELECTION,
                "note": "Single-hop keyphrase generation does not need similarity embeddings. Usage is callback-observed, not an invoice.",
            }
            (output_dir / "usage.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(stats))


if __name__ == "__main__":
    main()


"""
* Giải thích pipeline của hàm Generate with langchain docs : 

15 chunk từ Qdrant
        ↓
LangChain Document: page_content + metadata 
        ↓
gọi hàm enerate_with_langchain_docs(...) 
        ↓
1. Kiểm tra LLM và embedding model đã được cấu hình
        ↓
2. Dùng transforms được truyền vào ( xử lý trước khi gọi Synthesizer để gen testset)
   → KeyphrasesExtractor, gắn Keyphrase vào node (document tương ứng)
        ↓
3. Chuyển từng Document thành node
   → tạo knowledge graph
        ↓
4. Áp dụng transform vào graph
   → node có thêm keyphrases 
        ↓
5. Gọi generator.generate(...)
   → dùng persona và query_distribution
        ↓
6. FocusedSingleHop tạo các scenario
   → chọn node, keyphrase, persona, phong cách
        ↓
7. LLM dùng focused_prompt() và context nguồn
   → sinh câu hỏi + đáp án tham khảo
        ↓
8. Trả về Testset
        ↓
9. Code project chuyển thành list,
   map_sources() kiểm tra và gắn ID nguồn
        ↓
testset_raw.json
+ Thực chất, ở đây ta tạo ra Synthesis riêng (Prompt riêng, Instruction riêng), transform riêng (lọc ra Key phrase) 
mục đích cuối cùng là để tạo ra testset Single Hop chất lượng cao 

* Giải thích thành phần synthesizer : 
+ Synthesizer là thành phần nằm trong TestsetGenerator , nó lấy thông tin trong knowledge graph, tạo scenario 
nhiệm vụ cuối cùng của nó là tạo ra prompt yêu cầu LLM làm tác vụ Generate testset theo kiểu cấu hình nào đó
+ đầu tiên Synthesizer tạo ra Scenario từ các trường dữ liệu đã được config : 
    +Node nguồn (chunk)
    + Persona
    + keyphrase / term
    + nội dung chunk nguồn
    + style
    + length
 sau đó , sử dụng Instruction đã chuẩn bị sẵn để hướng dẫn LLM 
+ hướng dẫn trong prompt
        ↓
       LLM
        ↓
Câu hỏi + đáp án tham khảo

"""