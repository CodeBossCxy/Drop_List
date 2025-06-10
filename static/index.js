async function getContainersByPartNo() {
    const part_no_input = document.getElementById("part-no-input");
    // console.log("part_no_input", part_no_input);
    part_no_input.addEventListener("keydown", async (e) => {
        if (e.key === "Enter") {
            console.log("Enter key pressed")
            e.preventDefault();
            const workcenter_input = document.getElementById("Workcenter-input");
            console.log("workcenter_input", workcenter_input.value);
            console.log("part_no_input", part_no_input.value);
            fetch(`/part/${part_no_input.value}`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ "part_no": part_no_input.value }),
            }).then(response => response.json())
              .then(data => {
                console.log("--------------------------------");
                console.log(data);
                let table = '<table style="width: 100%;" display="block">';
                table += '<thead><tr><th>No</th><th>Serial No</th><th>Part No</th><th>Revision</th><th>Quantity</th><th>Location</th><th>Add Date</th></tr></thead>';
                table += '<tbody>';
                let container = null;
                data.dataframe.forEach((row, index) => {
                    // Check if the location is in our production locations list
                    // const inValidLocation = prodLocations.includes(row.Location);
                    // console.log(`Location ${row.Location} is ${inValidLocation ? 'invalid' : 'valid'}`);
                    
                    // // You can use this information to style the row or add validation
                    // const rowStyle = inValidLocation ? 'color: red' : '';

                    if(!prodLocations.includes(row.Location)){
                        table += `<tr class="clickable-row" style="cursor: pointer;">
                            <td>${index + 1}</td>
                            <td>${row.Serial_No}</td>
                            <td>${row.Part_No}</td>
                            <td>${row.Revision}</td>
                            <td>${row.Quantity}</td>
                            <td>${row.Location}</td>
                            <td>${row.Add_Date}</td>
                        </tr>`;
                    }
                });
                table += '</tbody></table>';
                document.getElementById('containers-table').innerHTML = table;
                
                document.querySelectorAll('.clickable-row').forEach(row => {
                    row.addEventListener('click', function () {
                        const cells = this.querySelectorAll("td");

                        const index = cells[0].textContent.trim();
                        const serial = cells[1].textContent.trim();
                        const part_no = cells[2].textContent.trim();
                        const revision = cells[3].textContent.trim();
                        const quantity = cells[4].textContent.trim();
                        const location = cells[5].textContent.trim();
                        const add_date = cells[6].textContent.trim();

                        console.log(index, serial, part_no, revision, quantity, location, add_date);

                        if (workcenter_input.value.length < 1) {
                            alert("Please enter the destination workcenter");
                            return;
                        }

                        const req_time = new Date().toISOString();
                        console.log('User clicked at:', req_time);
                        container = {
                            "serial_no": serial, 
                            "quantity": quantity, 
                            "location": location, 
                            "workcenter": workcenter_input.value, 
                            "part_no": part_no, 
                            "revision": revision, 
                            "req_time": req_time
                        };
                        
                        fetch(`/part/${part_no_input.value}/${serial}`, {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json"
                            },
                            body: JSON.stringify(container),
                        }).then(response => response.json())
                          .then(data => {
                            console.log(data);
                            // Remove the row from the table
                            this.remove();
                            // Update row numbers
                            document.querySelectorAll('.clickable-row').forEach((row, idx) => {
                                row.cells[0].textContent = idx + 1;
                            });
                        });
                    });
                });
            });
        }
    });
}

// function sendrequest(container){
//     // const socket = new WebSocket("ws://localhost:8000/ws");
//     if (window.currentSocket && window.currentSocket.readyState === WebSocket.OPEN) {
//         window.currentSocket.send(JSON.stringify(container));
//     } else {
//         console.warn("WebSocket is not open. Cannot send message.");
//     }
// }

// function createWebSocket() {
//     const socket = new WebSocket("wss://10.1.3.54:8002/ws");

//     socket.onopen = () => {
//         console.log("Connection Established");
//     };

//     socket.onclose = (event) => {
//         console.log("WebSocket closed, attempting to reconnect...", event.reason);
//         setTimeout(createWebSocket, 1000); // reconnect after 1 second
//     };

//     socket.onerror = (e) => {
//         console.error("WebSocket error", e);
//     };

//     window.currentSocket = socket;
// }

// // Initialize websocket
// createWebSocket();


getContainersByPartNo();
