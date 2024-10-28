function submitQuery() {
    const query = document.getElementById('query').value;

    fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
})
.then(response => response.json())
.then(data => {
    document.getElementById('response').innerText = data.response;
})
.catch(error => console.error('Error:', error));
}