function deleteIssue(id) {
    fetch(`/delete_issue/${id}`, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.deleted) {
                let row = document.getElementById(`row-${id}`);
                row.style.transition = "opacity 0.5s ease-out";
                row.style.opacity = "0";
                setTimeout(() => row.remove(), 500);
            }
        });
}

function updateStatus(id) {
    fetch(`/update_status/${id}`, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            document.getElementById(`status-${id}`).textContent = data.status;
        });
}
