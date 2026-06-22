// TypeScript interfaces — must mirror api/models.py exactly.
//
// Field name drift between these interfaces and the Pydantic shapes is
// silent: the page renders nothing because the destructure fails.
// Use snake_case here for any field that is snake_case in the Pydantic
// model — do not camelCase.

// TODO: declare the Entity interface with the fields used by /extract.

// TODO: declare the ExtractResponse interface returned by /extract.

// TODO: declare the KGResponse interface returned by /kg/query.

// TODO: declare the Citation interface used inside /rag/answer.

// TODO: declare the RAGResponse interface returned by /rag/answer.
export {};
