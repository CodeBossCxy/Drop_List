const socket = new WebSocket("ws://10.1.3.54:8002/ws");
const messages = document.getElementById("messages");

// Function to get barcode image URL for a location
function getBarcodeUrl(location) {
    return `https://barcode.orcascan.com/?type=Code128&data=${location}`;
}

socket.onmessage = function(event) {
    const t = document.getElementById("messages");
    const msg = document.createElement("li");
    msg.textContent = event.data;
    const data = JSON.parse(event.data);
    console.log("Received data in driver:", data);
    
    // Handle delete signal
    if (data.type === "delete") {
        console.log("Processing delete signal for serial:", data.serial_no);
        const tbody = document.getElementById("containerTableBody");
        const rows = tbody.getElementsByTagName("tr");
        let found = false;
        
        for (let row of rows) {
            const cells = row.getElementsByTagName("td");
            console.log("Checking row with serial:", cells[0].textContent);
            if (cells[0].textContent === data.serial_no) {
                console.log("Found matching row, removing it");
                tbody.removeChild(row);
                found = true;
                break;
            }
        }
        
        if (!found) {
            console.log("No matching row found for serial:", data.serial_no);
        }
        return;
    }

    // Handle normal container data
    console.log("Processing normal container data");
    const tbody = document.getElementById("containerTableBody");
    const row = document.createElement("tr");
    row.classList.add("adding-row");
    
    // Create row with barcode image
    row.innerHTML = `
        <td>${data.serial_no}</td>
        <td>${data.part_no}</td>
        <td>${data.revision}</td>
        <td>${data.quantity}</td>
        <td>${data.location}</td>
        <td><img src="${getBarcodeUrl(data.location)}" alt="Barcode for ${data.location}" style="height: 50px;"></td>
        <td>${data.workcenter}</td>
        <td><button class="delete-btn">Done</button></td>`;
    
    tbody.appendChild(row);

    row.querySelector(".delete-btn").addEventListener("click", () => {
        tbody.removeChild(row);
    }); 
    
    console.log("Added new row to table");
};

