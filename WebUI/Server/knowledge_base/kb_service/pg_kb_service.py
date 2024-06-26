from typing import List, Dict

from langchain.schema import Document
from langchain.vectorstores.pgvector import PGVector, DistanceStrategy
from sqlalchemy import text
from WebUI.configs.basicconfig import GetKbsConfig
from WebUI.Server.knowledge_base.kb_service.base import SupportedVSType, KBService, EmbeddingsFunAdapter, score_threshold_process
from WebUI.Server.knowledge_base.utils import KnowledgeFile
import shutil


class PGKBService(KBService):
    pg_vector: PGVector

    def _load_pg_vector(self):
        self.pg_vector = PGVector(embedding_function=EmbeddingsFunAdapter(self.embed_model),
                                  collection_name=self.kb_name,
                                  distance_strategy=DistanceStrategy.EUCLIDEAN,
                                  connection_string=GetKbsConfig("pg").get("connection_uri"))

    def get_doc_by_ids(self, ids: List[str]) -> List[Document]:
        with self.pg_vector.connect() as connect:
            ids_string = "('" + "','".join(ids) + "')"
            stmt = text("SELECT document, cmetadata FROM langchain_pg_embedding WHERE custom_id in " + ids_string)
            results = [Document(page_content=row[0], metadata=row[1]) for row in
                       connect.execute(stmt).fetchall()]
            return results

    # TODO:
    def del_doc_by_ids(self, ids: List[str]) -> bool:
        return super().del_doc_by_ids(ids)

    def do_init(self):
        self._load_pg_vector()

    def do_create_kb(self):
        pass

    def vs_type(self) -> str:
        return SupportedVSType.PG

    def do_drop_kb(self):
        with self.pg_vector.connect() as connect:
            connect.execute(text(f'''
                    DELETE FROM langchain_pg_embedding
                    WHERE collection_id IN (
                      SELECT uuid FROM langchain_pg_collection WHERE name = '{self.kb_name}'
                    );
                    DELETE FROM langchain_pg_collection WHERE name = '{self.kb_name}';
            '''))
            connect.commit()
            shutil.rmtree(self.kb_path)

    def do_search(self, query: str, top_k: int, score_threshold: float):
        self._load_pg_vector()
        embed_func = EmbeddingsFunAdapter(self.embed_model)
        embeddings = embed_func.embed_query(query)
        docs = self.pg_vector.similarity_search_with_score_by_vector(embeddings, top_k)
        return score_threshold_process(score_threshold, top_k, docs)

    def do_add_doc(self, docs: List[Document], **kwargs) -> List[Dict]:
        ids = self.pg_vector.add_documents(docs)
        doc_infos = [{"id": id, "metadata": doc.metadata} for id, doc in zip(ids, docs)]
        return doc_infos

    def do_delete_doc(self, kb_file: KnowledgeFile, **kwargs):
        with self.pg_vector.connect() as connect:
            filepath = kb_file.filepath.replace('\\', '\\\\')
            connect.execute(
                text(
                    ''' DELETE FROM langchain_pg_embedding WHERE cmetadata::jsonb @> '{"source": "filepath"}'::jsonb;'''.replace(
                        "filepath", filepath)))
            connect.commit()

    def do_clear_vs(self):
        self.pg_vector.delete_collection()
        self.pg_vector.create_collection()
