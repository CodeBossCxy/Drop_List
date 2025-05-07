
const socket = new WebSocket("ws://10.1.3.54:8002/ws");
const messages = document.getElementById("messages");

socket.onmessage = function(event) {
    const t = document.getElementById("messages");
    const msg = document.createElement("li");
    msg.textContent = event.data;
    container = JSON.parse(event.data);
    console.log(typeof container);
    console.log("event.data: \n", container);
    const tbody = document.getElementById("containerTableBody");
    const row = document.createElement("tr");
    row.classList.add("adding-row");
    row.innerHTML = `
        <td>${container.serial_no}</td>
        <td>${container.quantity}</td>
        <td>${container.location}</td>
        <td>${container.workcenter}</td>
        <td><button class="delete-btn">Done</button></td>`;
    row.querySelector(".delete-btn").addEventListener("click", () => {
        tbody.removeChild(row);
    }); 
    
    tbody.appendChild(row);
    console.log("table: \n", tbody);
};

