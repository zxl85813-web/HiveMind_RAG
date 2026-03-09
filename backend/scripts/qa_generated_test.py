import pytest


# Mocked classes and functions
class InMemoryAbstractIndex:
    def __init__(self):
        self.index = {}

    def add_abstract(self, doc_id, title, tags, doc_type, date):
        self.index[doc_id] = {"title": title, "tags": tags, "type": doc_type, "date": date}

    def route_query(self, tags):
        results = []
        for doc_id, data in self.index.items():
            if set(tags).issubset(set(data["tags"])):
                results.append(data)
        return results


class MemoryService:
    def __init__(self, abstract_index, vector_db):
        self.abstract_index = abstract_index
        self.vector_db = vector_db

    async def add_memory(self, full_text):
        # Mocking the slow track
        self.vector_db.add_document(full_text)

        # Mocking the fast track
        extracted_data = self._extract_and_index_abstract(full_text)
        self.abstract_index.add_abstract(**extracted_data)

    def _extract_and_index_abstract(self, full_text):
        # Mocking the extraction process
        return {
            "doc_id": "mock_doc_id",
            "title": "mock_title",
            "tags": ["mock_tag"],
            "doc_type": "mock_type",
            "date": "mock_date",
        }


class ChatService:
    def __init__(self, abstract_index, vector_db):
        self.abstract_index = abstract_index
        self.vector_db = vector_db

    def chat_stream(self, user_query):
        keywords = self._extract_keywords(user_query)
        radar_results = self.abstract_index.route_query(tags=keywords)
        deep_context = self.vector_db.search(user_query)
        return {"hot_memory": radar_results, "deep_context": deep_context}

    def _extract_keywords(self, user_query):
        # Mocking keyword extraction
        return ["mock_keyword"]


class VectorDB:
    def __init__(self):
        self.documents = []

    def add_document(self, document):
        self.documents.append(document)

    def search(self, query):
        # Mocking search
        return ["mock_document"]


# Test cases
@pytest.fixture
def mock_abstract_index():
    return InMemoryAbstractIndex()


@pytest.fixture
def mock_vector_db():
    return VectorDB()


@pytest.fixture
def memory_service(mock_abstract_index, mock_vector_db):
    return MemoryService(mock_abstract_index, mock_vector_db)


@pytest.fixture
def chat_service(mock_abstract_index, mock_vector_db):
    return ChatService(mock_abstract_index, mock_vector_db)


@pytest.mark.asyncio
async def test_add_memory(memory_service, mock_abstract_index, mock_vector_db):
    full_text = "This is a test document."
    await memory_service.add_memory(full_text)

    assert mock_vector_db.documents == [full_text]
    assert mock_abstract_index.index == {
        "mock_doc_id": {"title": "mock_title", "tags": ["mock_tag"], "type": "mock_type", "date": "mock_date"}
    }


def test_chat_stream(chat_service, mock_abstract_index, mock_vector_db):
    user_query = "Test query"
    result = chat_service.chat_stream(user_query)

    assert result == {"hot_memory": [], "deep_context": ["mock_document"]}


def test_route_query(mock_abstract_index):
    mock_abstract_index.add_abstract("doc1", "title1", ["tag1", "tag2"], "type1", "date1")
    mock_abstract_index.add_abstract("doc2", "title2", ["tag2", "tag3"], "type2", "date2")

    results = mock_abstract_index.route_query(["tag1"])
    assert results == [{"title": "title1", "tags": ["tag1", "tag2"], "type": "type1", "date": "date1"}]
