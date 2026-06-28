import { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css'; // Creeremo lo stile tra un attimo

function App() {
  // Lo "Stato" in React: qui parcheggiamo i film non appena arrivano dal Gateway
  const [movies, setMovies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Il ciclo di vita: questa funzione scatta in automatico non appena la pagina viene caricata nel browser
  useEffect(() => {
    axios.get('http://localhost:8000/api/movies')
      .then((response) => {
        setMovies(response.data); // Salviamo i 20 film nello stato
        setLoading(false);
      })
      .catch((err) => {
        console.error("Errore nel recupero dei film:", err);
        setError("Impossibile caricare i film dal server.");
        setLoading(false);
      });
  }, []);

  if (loading) return <div className="loading">Caricamento dei film in corso... 🍿</div>;
  if (error) return <div className="error-message">❌ {error}</div>;

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>🎬 Movie Recommender Engine</h1>
        <p>Benvenuto nell'app! Ecco i film popolari estratti da MongoDB:</p>
      </header>

      {/* La griglia dei film */}
      <div className="movies-grid">
        {movies.map((movie) => (
          <div key={movie.id} className="movie-card">
            {movie.poster_path ? (
              <img 
                src={`https://image.tmdb.org/t/p/w500${movie.poster_path}`} 
                alt={movie.title} 
                className="movie-poster"
              />
            ) : (
              <div className="no-poster">Nessuna Locandina</div>
            )}
            <div className="movie-info">
              <h3>{movie.title}</h3>
              <div className="movie-meta">
                <span className="rating">⭐ {movie.vote_average?.toFixed(1)}</span>
                <span className="lang">🌐 {movie.original_language?.toUpperCase()}</span>
              </div>
              <p className="movie-overview">
                {movie.overview ? movie.overview.substring(0, 120) + "..." : "Nessuna trama disponibile."}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;