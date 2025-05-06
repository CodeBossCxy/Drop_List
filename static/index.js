async function getContainersByPartNo() {

    const part_no_input = document.getElementById("part-no-input");
    // console.log("part_no_input", part_no_input);
    part_no_input.addEventListener("keydown", async (e) => {
        if (e.key === "Enter") {
            console.log("Enter key pressed")
            e.preventDefault();
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
                table += '<thead><tr><th>Serial No</th><th>Quantity</th><th>Location</th></tr></thead>';
                table += '<tbody>';
                let container = null;
                data.dataframe.forEach((row, index) => {
                    if (index === 0) {
                        table += `<tr class="clickable-row" style="cursor: pointer;"><td>${row.Serial_No}</td><td>${row.Quantity}</td><td>${row.Location}</td></tr>`;
                        container = row
                    } else {
                        table += `<tr><td>${row.Serial_No}</td><td>${row.Quantity}</td><td>${row.Location}</td></tr>`;
                    }
                });
                table += '</tbody></table>';
                document.getElementById('containers-table').innerHTML = table;
                const firstRow = document.querySelector('.clickable-row');
                console.log("firstRow", firstRow);
                if (firstRow) {
                    firstRow.addEventListener('click', () => {
                        console.log("First row clicked");
                        fetch(`/part/${part_no_input.value}/${container.Serial_No}`, {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json"
                            },
                            body: JSON.stringify({"serial_no": container.Serial_No }),
                        }).then(response => response.json())
                          .then(data => {
                            console.log(data);
                            sendrequest(container);
                          });
                    });
                }
            });
        }
    });
}

function sendrequest(container){
    // const socket = new WebSocket("ws://localhost:8000/ws");
    socket.send(JSON.stringify(container));
}

const socket = new WebSocket("ws://localhost:8000/ws");
socket.onopen = () => {
    console.log("Connection Established");
}
socket.onerror = (e) => {
    console.error("WebSocket error", e);
};


getContainersByPartNo();


