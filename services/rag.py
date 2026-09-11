"""Small evidence-first RAG store. It can be replaced by Chroma/pgvector in production."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceChunk:
    id: str
    text: str
    source_type: str
    product_id: str | None = None


KNOWLEDGE = (
    EvidenceChunk("knowledge:ip68", "IP68 表示设备具备规定条件下的防尘和防水能力；实际水深、时长及保修范围以厂商说明为准。", "glossary"),
    EvidenceChunk("knowledge:oled", "OLED 是像素自发光显示技术，通常有较高对比度和深黑表现。", "glossary"),
    EvidenceChunk("knowledge:anc", "主动降噪通过麦克风采集环境声并生成反向声波，主要降低持续的低频噪声。", "glossary"),
)


class RagService:
    def retrieve(self, query: str, top_k: int = 3) -> list[EvidenceChunk]:
        terms = set(query.lower().replace("主动降噪", "anc").split()) | {"ip68" if "ip68" in query.lower() else ""}
        scored = [(sum(term in chunk.id.lower() or term in chunk.text.lower() for term in terms), chunk) for chunk in KNOWLEDGE]
        return [chunk for score, chunk in sorted(scored, reverse=True, key=lambda item: item[0]) if score][:top_k]

