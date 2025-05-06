
const socket = new WebSocket("ws://localhost:8000/ws");
const messages = document.getElementById("messages");

socket.onmessage = function(event) {
    const t = document.getElementById("messages");
    const msg = document.createElement("li");
    msg.textContent = event.data;
    container = JSON.parse(event.data);
    console.log("event.data", container);
    let table = '<table style="width: 100%;" display="block">';
    table += '<thead><tr><th>Serial No</th><th>Quantity</th><th>Location</th></tr></thead>';
    table += '<tbody>'; 
    table += `<tr><td>${container.Serial_No}</td><td>${container.Quantity}</td><td>${container.Location}</td></tr>`;
    table += '</tbody></table>';
    console.log("table: \n", table);
    t.innerHTML = table;
};
