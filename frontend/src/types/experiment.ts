// Experiment domain types now live in @/api/types (ApiExperiment,
// ApiExperimentResult, etc.) - this file intentionally has nothing left to
// export. Kept as an empty module rather than deleted so `export * from
// './experiment'` in index.ts doesn't need touching if a future
// presentational-only experiment type is needed here again.
export {};
