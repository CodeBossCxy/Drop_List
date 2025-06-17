// Loading spinner functions
function showLoading() {
    console.log("Showing loading spinner");
    document.getElementById('loadingSpinner').style.display = 'block';
    document.getElementById('loadingOverlay').style.display = 'block';
}

function hideLoading() {
    console.log("Hiding loading spinner");
    document.getElementById('loadingSpinner').style.display = 'none';
    document.getElementById('loadingOverlay').style.display = 'none';
}

// Function to clear containers table
function clearContainersTable() {
    const containersTable = document.getElementById('containers-table');
    containersTable.innerHTML = '';
}

// Function to display message
function displayMessage(message) {
    const containersTable = document.getElementById('containers-table');
    containersTable.innerHTML = `
        <div class="alert alert-info text-center mt-5" role="alert">
            ${message}
        </div>
    `;
}

// Function to fetch existing requests from database
async function fetchExistingRequests() {
    console.log("Fetching existing requests");
    try {
        const response = await fetch('/api/requests');
        if (!response.ok) {
            throw new Error('Failed to fetch existing requests');
        }
        const requests = await response.json();
        const result = new Set(requests.map(req => req.serial_no));
        console.log("result", result);
        return result;
    } catch (error) {
        console.error('Error fetching existing requests:', error);
        return new Set(); // Return empty set if there's an error
    }
}

// Modify your existing fetch calls to use the loading spinner
async function fetchContainers(partNo) {
    showLoading();
    try {
        // Fetch available containers
        const response = await fetch(`/part/${partNo}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        const data = await response.json();
        
        // Check if the dataframe is empty
        if (!data.dataframe || data.dataframe.length === 0) {
            clearContainersTable();
            displayMessage("No available container");
            return;
        }
        
        // Update the UI with the data
        updateContainersTable(data.dataframe);
    } catch (error) {
        console.error('Error:', error);
        clearContainersTable();
        displayMessage("Error fetching data. Please try again.");
    } finally {
        hideLoading();
    }
}

// Function to update containers table
function updateContainersTable(data) {
    const containersTable = document.getElementById('containers-table');
    // Clear existing content
    containersTable.innerHTML = '';
    
    // Create table
    const table = document.createElement('table');
    table.className = 'table table-striped table-hover mt-5';
    
    // Create table header
    const thead = document.createElement('thead');
    thead.innerHTML = `
        <tr>
            <th>Serial No</th>
            <th>Part No</th>
            <th>Revision</th>
            <th>Quantity</th>
            <th>Location</th>
            <th>Action</th>
        </tr>
    `;
    
    // Create table body
    const tbody = document.createElement('tbody');
    data.forEach(item => {
        const tr = document.createElement('tr');
        tr.id = `row-${item.Serial_No}`; // Add unique ID to each row
        
        // Add strikethrough and opacity if already requested
        if (item.isRequested) {
            tr.style.textDecoration = 'line-through';
            tr.style.opacity = '0.6';
        }
        
        tr.innerHTML = `
            <td>${item.Serial_No}</td>
            <td>${item.Part_No}</td>
            <td>${item.Revision}</td>
            <td>${item.Quantity}</td>
            <td>${item.Location}</td>
            <td>
                <button class="btn ${item.isRequested ? 'btn-secondary' : 'btn-primary'} btn-sm" 
                        onclick="handleRequest('${item.Serial_No}', '${item.Part_No}', this)"
                        ${item.isRequested ? 'disabled' : ''}>
                    ${item.isRequested ? 'Requested' : 'Request'}
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
    
    table.appendChild(thead);
    table.appendChild(tbody);
    containersTable.appendChild(table);
}

// Function to handle request button click
async function handleRequest(serialNo, partNo, button) {
    // Disable the button to prevent multiple clicks
    button.disabled = true;
    button.textContent = 'Requested';
    button.className = 'btn btn-secondary btn-sm';
    
    // Add strikethrough to the row
    const row = document.getElementById(`row-${serialNo}`);
    if (row) {
        row.style.textDecoration = 'line-through';
        row.style.opacity = '0.6';
    }
    
    try {
        const workcenter = document.getElementById('Workcenter-input').value;
        const revision = document.getElementById('shipper-number-input').value;
        
        if (!workcenter) {
            alert('Please enter a workcenter');
            return;
        }
        
        const response = await fetch(`/part/${partNo}/${serialNo}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                workcenter: workcenter,
                revision: revision,
                location: row.querySelector('td:nth-child(5)').textContent,
                quantity: row.querySelector('td:nth-child(4)').textContent,
                req_time: new Date().toISOString()
            })
        });
        
        if (!response.ok) {
            throw new Error('Request failed');
        }
        
        // Optional: Show success message
        const successAlert = document.createElement('div');
        successAlert.className = 'alert alert-success alert-dismissible fade show mt-3';
        successAlert.innerHTML = `
            Container ${serialNo} requested successfully
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        document.getElementById('containers-table').insertBefore(successAlert, document.getElementById('containers-table').firstChild);
        
    } catch (error) {
        console.error('Error:', error);
        // Revert the button and row state if request fails
        button.disabled = false;
        button.textContent = 'Request';
        button.className = 'btn btn-primary btn-sm';
        if (row) {
            row.style.textDecoration = 'none';
            row.style.opacity = '1';
        }
        
        // Show error message
        const errorAlert = document.createElement('div');
        errorAlert.className = 'alert alert-danger alert-dismissible fade show mt-3';
        errorAlert.innerHTML = `
            Failed to request container ${serialNo}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        document.getElementById('containers-table').insertBefore(errorAlert, document.getElementById('containers-table').firstChild);
    }
}

// Add event listeners to your inputs
document.getElementById('part-no-input').addEventListener('keydown', async (e) => {
    // const partNo = e.target.value;
    // if (partNo && e.key === "Enter") {
    //     const data = await fetchContainers(partNo);
    // }
    enterKeyPressed(e);
});

document.getElementById('Workcenter-input').addEventListener('keydown', async (e) => {
    enterKeyPressed(e);
});

document.getElementById('shipper-number-input').addEventListener('keydown', async (e) => {
    enterKeyPressed(e);
});

async function enterKeyPressed(e) {
    const partNo = document.getElementById('part-no-input').value;
    console.log("partNo", partNo);
    if (partNo && e.key === "Enter") {
        const data = await fetchContainers(partNo);
    }
    if (!partNo) {
        console.log("No part number entered");
        clearContainersTable();
        displayMessage("Please enter a part number");
    }
}

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


// getContainersByPartNo();
