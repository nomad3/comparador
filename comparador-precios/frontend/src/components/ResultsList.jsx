import React from 'react';
import useSearchStore from '../store/searchStore';
import ResultCard from './ResultCard';
import './ResultsList.css'; // We'll create this CSS file next

function ResultsList() {
  const { results, isLoading, error, query } = useSearchStore(
    // Selector to only re-render when these specific values change
    (state) => ({
      results: state.results,
      isLoading: state.isLoading,
      error: state.error,
      query: state.query // Need query to know if a search was attempted
    })
  );

  // Determine if a search has been attempted (query exists but not loading)
  // This helps differentiate initial state from "no results found" state.
  const searchAttempted = query.length >= 3 && !isLoading;

  if (isLoading) {
    // Optional: Add a more sophisticated loading spinner component
    return <div className="results-loading">Cargando resultados...</div>;
  }

  if (error) {
    return <div className="results-error">Error: {error}</div>;
  }

  // Show "No results" only if a search was attempted and yielded nothing
  if (searchAttempted && results.length === 0) {
    return <div className="results-empty">No se encontraron resultados para "{query}".</div>;
  }

  // Don't render anything if no search has been attempted yet
  if (!searchAttempted && results.length === 0) {
      return null;
  }

  // Render the list of results
  return (
    <div className="results-list">
      {results.map((result, index) => (
        // Using product_url as key assumes it's unique per result item
        <ResultCard key={`${result.product_url}-${index}`} result={result} />
      ))}
    </div>
  );
}

export default ResultsList;
