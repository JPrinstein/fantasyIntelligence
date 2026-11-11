
import unittest

from rag.chunker import chunk_text, chunk_documents


class TestChunker(unittest.TestCase):

    def test_preserves_paragraph_order(self):
        """Paragraphs must remain in their original order."""
        text = (
            "First paragraph has important information.\n\n"
            "Second paragraph contains different information.\n\n"
            "Third paragraph concludes the document."
        )

        chunks = chunk_text(text, chunk_size=5, overlap=0)

        self.assertEqual(chunks, [
            "First paragraph has important information.",
            "Second paragraph contains different information.",
            "Third paragraph concludes the document."
        ])

    def test_preserves_duplicate_paragraphs(self):
        """Identical paragraphs must not be silently removed."""
        text = (
            "This paragraph appears twice.\n\n"
            "This paragraph appears twice."
        )

        chunks = chunk_text(text, chunk_size=4, overlap=0)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0], chunks[1])

    def test_combines_paragraphs_within_limit(self):
        """Small paragraphs should share a chunk when they fit."""
        text = (
            "First short paragraph.\n\n"
            "Second short paragraph."
        )

        chunks = chunk_text(text, chunk_size=6, overlap=0)

        self.assertEqual(chunks, [
            "First short paragraph. Second short paragraph."
        ])

    def test_keeps_large_paragraph_intact(self):
        """A paragraph may exceed the target rather than be cut."""
        text = "This paragraph has more than five words total."

        chunks = chunk_text(text, chunk_size=5, overlap=0)

        self.assertEqual(chunks, [text])

    def test_empty_document(self):
        """Empty or whitespace-only documents produce no chunks."""
        self.assertEqual(chunk_text(""), [])
        self.assertEqual(chunk_text("   \n\n   "), [])

    def test_preserves_source_metadata(self):
        """Chunks must retain their source and document identity."""
        documents = [
            {
                "source": "quarterbacks.txt",
                "text": "First paragraph.\n\nSecond paragraph."
            }
        ]

        chunks = chunk_documents(
            documents,
            chunk_size=2,
            overlap=0
        )

        self.assertEqual(len(chunks), 2)

        self.assertEqual(
            [chunk["chunk_id"] for chunk in chunks],
            [0, 1]
        )

        for chunk in chunks:
            self.assertEqual(chunk["source"], "quarterbacks.txt")
            self.assertEqual(chunk["document_id"], "quarterbacks")


if __name__ == "__main__":
    unittest.main()
