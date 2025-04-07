import React from 'react';
import SearchBar from './components/SearchBar';
import ResultsList from './components/ResultsList';
import './App.css'; // Keep or modify default App styles

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>Comparador de Precios MVP</h1>
      </header>
      <main>
        <SearchBar />
        <ResultsList />
      </main>
      <footer className="App-footer">
        {/* Optional Footer Content */}
        <p>&copy; {new Date().getFullYear()} Comparador Inc.</p>
      </footer>
    </div>
  );
}

export default App;
