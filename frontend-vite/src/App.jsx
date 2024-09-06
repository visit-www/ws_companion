import { useEffect, useState } from 'react';

function App() {
  const [data, setData] = useState(null);  // State to store fetched data

  useEffect(() => {
    console.log('useEffect is running');

    const apiUrl = `${import.meta.env.VITE_BACKEND_URL}/api/data`;
    console.log('Fetching data from:', apiUrl);

    fetch(apiUrl)
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();  // Converts the response to JSON
      })
      .then(data => {
        console.log('Data from Flask:', data);  // Logs the fetched data
        setData(data);  // Updates state with the fetched data
      })
      .catch(error => {
        console.error('Error fetching data:', error);  // Logs any errors encountered
      });
  }, []);  // Runs once when the component mounts

  return (
    <div>
      <h1>React is fetching data from Flask!</h1>
      {data ? (
        <pre>{JSON.stringify(data, null, 2)}</pre>  // Displays the fetched data
      ) : (
        <p>Loading data...</p>
      )}
    </div>
  );
}

export default App;