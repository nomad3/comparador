import React from 'react';
import useSearchStore from '../store/searchStore';
import './SearchBar.css'; // We'll create this CSS file next

function SearchBar() {
  const { query, setQuery, searchProducts, isLoading, forceSearch, message, jobId } = useSearchStore();

  const handleInputChange = (event) => {
    setQuery(event.target.value);
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    searchProducts(); // Trigger search without forcing refresh
  };

  const handleForceSearch = () => {
    forceSearch(); // Trigger search forcing refresh
  }

  return (
    <div className="search-bar-container">
      <form onSubmit={handleSubmit} className="search-form">
        <input
          type="text"
          placeholder="Buscar producto (ej: laptop gamer, smartphone)..."
          value={query}
          onChange={handleInputChange}
          className="search-input"
          disabled={isLoading}
        />
        <button type="submit" className="search-button" disabled={isLoading || query.length < 3}>
          {isLoading ? 'Buscando...' : 'Buscar'}
        </button>
        <button
          type="button"
          onClick={handleForceSearch}
          className="force-search-button"
          title="Forzar actualización (ignorar caché)"
          disabled={isLoading || query.length < 3}
        >
          Actualizar
        </button>
      </form>
      {message && <p className="search-message">ℹ️ {message} {jobId ? `(Job ID: ${jobId})` : ''}</p>}
    </div>
  );
}

export default SearchBar;
