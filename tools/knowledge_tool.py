from services.rag import EvidenceChunk, RagService


class KnowledgeTool:
    def __init__(self): self.rag = RagService()
    def retrieve_knowledge(self, query: str, top_k: int = 3) -> list[EvidenceChunk]: return self.rag.retrieve(query, top_k)
