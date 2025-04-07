import React from 'react';
import './ResultCard.css'; // We'll create this CSS file next

function ResultCard({ result }) {
  // Helper to format price (basic example)
  const formatPrice = (price, currency) => {
    try {
      // Attempt to parse the price string back to a number if needed
      const numericPrice = typeof price === 'string' ? parseFloat(price.replace(/[^0-9,-]+/g,"").replace(",", ".")) : price;
      if (isNaN(numericPrice)) {
          throw new Error("Invalid price format after cleaning");
      }
      return new Intl.NumberFormat('es-CL', { style: 'currency', currency: currency }).format(numericPrice);
    } catch (e) {
      console.error("Error formatting price:", price, e);
      return `${currency} ${price}`; // Fallback
    }
  };

  return (
    <div className="result-card">
      {/* <img src={result.image_url || 'placeholder.png'} alt={result.source_product_name} className="result-image" /> */}
      <div className="result-details">
        <h3 className="result-name">{result.source_product_name}</h3>
        <p className="result-source">Vendido por: <strong>{result.source_name}</strong></p>
        <p className="result-price">{formatPrice(result.price, result.currency)}</p>
        <p className="result-scraped-at">Actualizado: {result.scraped_at}</p> {/* Already formatted in store */}
        <a
          href={result.product_url}
          target="_blank"
          rel="noopener noreferrer"
          className="result-link"
        >
          Ver en {result.source_name}
        </a>
      </div>
    </div>
  );
}

export default ResultCard;
