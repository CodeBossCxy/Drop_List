// const socket = new WebSocket("wss://10.1.3.54:8002/ws");
const messages = document.getElementById("messages");

// Function to get barcode image URL for a location
function getBarcodeUrl(location) {
    return `https://barcode.orcascan.com/?type=qr&data=${location}`;
}

// Function to create a row element
function createRowElement(data) {
    const row = document.createElement("tr");
    row.classList.add("adding-row");
    
    row.innerHTML = `
        <td>${data.serial_no}</td>
        <td>${data.part_no}</td>
        <td>${data.revision}</td>
        <td>${data.quantity}</td>
        <td>${data.location}</td>
        <td><img src="${getBarcodeUrl(data.location)}" alt="Barcode for ${data.location}" class="barcode-img"></td>
        <td>${data.deliver_to}</td>
        <td>
            <button class="delete-btn" onclick="handleDelete('${data.serial_no}', this)">
                Done
            </button>
        </td>
    `;
    
    return row;
}

// Function to handle delete button click
async function handleDelete(serialNo, button) {
    try {
        const response = await fetch(`/api/requests/${serialNo}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            const row = button.closest('tr');
            row.style.opacity = '0';
            setTimeout(() => {
                row.remove();
            }, 500);
        } else {
            console.error('Failed to delete request');
            alert('Failed to delete request. Please try again.');
        }
    } catch (error) {
        console.error('Error deleting request:', error);
        alert('Error deleting request. Please try again.');
    }
}

// Function to fetch and display requests
async function fetchAndDisplayRequests() {
    try {
        const response = await fetch('/api/requests');
        const requests = await response.json();
        
        const tbody = document.getElementById("containerTableBody");
        tbody.innerHTML = ''; // Clear existing rows
        
        requests.forEach(data => {
            const row = createRowElement(data);
            tbody.appendChild(row);
        });
    } catch (error) {
        console.error('Error fetching requests:', error);
    }
}

// Fetch requests when page loads
document.addEventListener('DOMContentLoaded', fetchAndDisplayRequests);

// Set up polling to refresh data every 5 seconds
setInterval(fetchAndDisplayRequests, 5000);

// socket.onopen = function(e) {
//     console.log("WebSocket connection established");
// };

// socket.onclose = function(event) {
//     console.log('WebSocket connection closed. Attempting to reconnect...');
//     setTimeout(() => {
//         socket = new WebSocket(`ws://${window.location.host}/ws`);
//     }, 1000);
// };

// socket.onerror = function(error) {
//     console.error('WebSocket error:', error);
// };

// socket.onmessage = function(event) {
//     const data = JSON.parse(event.data);
//     console.log("Received data in driver:", data);
    
//     // Handle delete signal
//     if (data.type === "delete") {
//         console.log("Processing delete signal for serial:", data.serial_no);
//         const tbody = document.getElementById("containerTableBody");
//         const rows = tbody.getElementsByTagName("tr");
//         let found = false;
        
//         for (let row of rows) {
//             const cells = row.getElementsByTagName("td");
//             if (cells[0].textContent === data.serial_no) {
//                 row.style.opacity = '0';
//                 setTimeout(() => {
//                     row.remove();
//                 }, 500);
//                 found = true;
//                 break;
//             }
//         }
        
//         if (!found) {
//             console.log("No matching row found for serial:", data.serial_no);
//         }
//         return;
//     }

//     // Handle normal container data
//     console.log("Processing normal container data");
//     const tbody = document.getElementById("containerTableBody");
//     const row = createRowElement(data);
//     tbody.appendChild(row);
    
//     console.log("Added new row to table");
// };

