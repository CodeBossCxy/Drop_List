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
                console.log(data);
                let table = '<table style="width: 100%;" display="block">';
                table += '<thead><tr><th>No</th><th>Serial No</th><th>Quantity</th><th>Location</th></tr></thead>';
                table += '<tbody>';
                let container = null;
                data.dataframe.forEach((row, index) => {
                    table += `<tr class="clickable-row" style="cursor: pointer;"><td>${index + 1}</td><td>${row.Serial_No}</td><td>${row.Quantity}</td><td>${row.Location}</td></tr>`;
                    // if (index === 0) {
                    //     table += `<tr class="clickable-row" style="cursor: pointer;"><td>${index + 1}</td><td>${row.Serial_No}</td><td>${row.Quantity}</td><td>${row.Location}</td></tr>`;
                    //     container = row
                    // } else {
                    //     table += `<tr><td>${index + 1}</td><td>${row.Serial_No}</td><td>${row.Quantity}</td><td>${row.Location}</td></tr>`;
                    // }
                });
                table += '</tbody></table>';
                document.getElementById('containers-table').innerHTML = table;
                document.querySelectorAll('.clickable-row').forEach(row => {
                    row.addEventListener('click', function () {
                        const cells = this.querySelectorAll("td");

                        const index = cells[0].textContent.trim();
                        const serial = cells[1].textContent.trim();
                        const quantity = cells[2].textContent.trim();
                        const location = cells[3].textContent.trim();

                        console.log(index, serial, quantity, location);

                        if (workcenter_input.value.length < 1) {
                            alert("Please enter the destination workcenter");
                            return;
                        }
                        container = {"serial_no": serial, "quantity": quantity, "location": location, "workcenter": workcenter_input.value }
                        console.log("row clicked: ", index);
                        fetch(`/part/${part_no_input.value}/${serial}`, {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json"
                            },
                            body: container,
                        }).then(response => response.json())
                          .then(data => {
                            console.log(data);
                            sendrequest(container);
                        });
                    });
                });
            });
        }
    });
}

function sendrequest(container){
    // const socket = new WebSocket("ws://localhost:8000/ws");
    socket.send(JSON.stringify(container));
}

const socket = new WebSocket("ws://10.1.3.54:8002/ws");
socket.onopen = () => {
    console.log("Connection Established");
}

socket.onclose = (event) => {
    console.log("WebSocket closed, attempting to reconnect...", event.reason);
    setTimeout(createWebSocket, 1000); // reconnect after 1 second
};

socket.onerror = (e) => {
    console.error("WebSocket error", e);
};


getContainersByPartNo();


