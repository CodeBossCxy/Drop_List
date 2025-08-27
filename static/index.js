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
        const responseText = await response.text();
        let requests;
        try {
            requests = JSON.parse(responseText);
        } catch (jsonError) {
            console.error('Failed to parse JSON response:', jsonError);
            console.error('Response text:', responseText);
            throw new Error('Invalid JSON response from server');
        }
        const result = new Set(requests.map(req => req.serial_no));
        console.log("result", result);
        return result;
    } catch (error) {
        console.error('Error fetching existing requests:', error);
        return new Set(); // Return empty set if there's an error
    }
}
async function fetchContainerInfo(serialNo) {
    console.log('\n=== FETCH CONTAINER INFO START ===');
    console.log('fetchContainerInfo called with serialNo:', serialNo);
    
    showLoading();
    try {
        console.log('Making API call to:', `/${serialNo}`);
        
        const response = await fetch(`/${serialNo}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }   
        });
        
        console.log('API response status:', response.status, response.statusText);
        
        const responseText = await response.text();
        let data;
        try {
            data = JSON.parse(responseText);
        } catch (jsonError) {
            console.error('Failed to parse JSON response:', jsonError);
            console.error('Response text:', responseText);
            throw new Error('Invalid JSON response from server');
        }
        console.log('API response data:', data);
        
        // DETAILED DATA INSPECTION
        console.log('🔍 DETAILED API RESPONSE ANALYSIS:');
        console.log('- data type:', typeof data);
        console.log('- data keys:', Object.keys(data));
        console.log('- data.dataframe exists:', !!data.dataframe);
        console.log('- data.dataframe type:', typeof data.dataframe);
        if (data.dataframe) {
            console.log('- data.dataframe length:', data.dataframe.length);
            console.log('- data.dataframe[0]:', data.dataframe[0]);
        }
        
        // Check if the dataframe is empty
        if (!data.dataframe || data.dataframe.length === 0) {
            console.log('❌ No data found - showing "No available container" message');
            console.log('- data.dataframe is:', data.dataframe);
            clearContainersTable();
            displayMessage("No available container");
            return;
        }
        
        console.log('✅ Data found - calling updateContainersTable with:', data.dataframe.length, 'items');
        console.log('- First item:', data.dataframe[0]);
        
        // Update the UI with the data
        updateContainerTable(data.dataframe);
    } catch (error) {
        console.error('Error in fetchContainerInfo:', error);
        clearContainersTable();
        displayMessage("Error fetching data. Please try again.");
    } finally {
        hideLoading();
        console.log('=== FETCH CONTAINER INFO END ===\n');
    }
}

// Modify your existing fetch calls to use the loading spinner
async function fetchContainers(partNo) {
    console.log('\n=== FETCH CONTAINERS START ===');
    console.log('fetchContainers called with partNo:', partNo);
    
    showLoading();
    try {
        console.log('Making API call to:', `/part/${partNo}`);
        
        // Fetch available containers
        const response = await fetch(`/part/${partNo}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        console.log('API response status:', response.status, response.statusText);
        
        const responseText = await response.text();
        let data;
        try {
            data = JSON.parse(responseText);
        } catch (jsonError) {
            console.error('Failed to parse JSON response:', jsonError);
            console.error('Response text:', responseText);
            throw new Error('Invalid JSON response from server');
        }
        console.log('API response data:', data);
        
        // DETAILED DATA INSPECTION
        console.log('🔍 DETAILED API RESPONSE ANALYSIS:');
        console.log('- data type:', typeof data);
        console.log('- data keys:', Object.keys(data));
        console.log('- data.dataframe exists:', !!data.dataframe);
        console.log('- data.dataframe type:', typeof data.dataframe);
        if (data.dataframe) {
            console.log('- data.dataframe length:', data.dataframe.length);
            console.log('- data.dataframe[0]:', data.dataframe[0]);
        }
        
        // Check if the dataframe is empty
        if (!data.dataframe || data.dataframe.length === 0) {
            console.log('❌ No data found - showing "No available container" message');
            console.log('- data.dataframe is:', data.dataframe);
            clearContainersTable();
            displayMessage("No available container");
            return;
        }
        
        console.log('✅ Data found - calling updateContainersTable with:', data.dataframe.length, 'items');
        console.log('- First item:', data.dataframe[0]);
        
        // Update the UI with the data
        updateContainersTable(data.dataframe);
    } catch (error) {
        console.error('Error in fetchContainers:', error);
        clearContainersTable();
        displayMessage("Error fetching data. Please try again.");
    } finally {
        hideLoading();
        console.log('=== FETCH CONTAINERS END ===\n');
    }
}

function updateContainerTable(data) {
    console.log('=== updateContainersTable START ===');
    console.log('updateContainersTable called with data:', data);
    console.log('Data length:', data.length);
    
    const containersTable = document.getElementById('containers-table');
    console.log('containersTable element found:', !!containersTable);
    
    // Clear existing content
    containersTable.innerHTML = '';
    console.log('containersTable cleared');
    
    // Create table
    const table = document.createElement('table');
    table.className = 'table table-hover mt-5'; // Removed table-striped to avoid conflicts
    console.log('Table created with classes:', table.className);
    
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
    console.log('Table header created');
    
    // Create table body
    const tbody = document.createElement('tbody');
    console.log('Table body created');
    
    data.forEach((item, index) => {
        console.log(`\n--- Processing row ${index} ---`);
        console.log(`Row ${index} data:`, item);
        
        const tr = document.createElement('tr');
        tr.id = `row-${item.Serial_No}`; // Add unique ID to each row
        console.log(`Created tr element with ID: ${tr.id}`);
        
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
        console.log(`Row ${index} innerHTML set`);
        
        // Add strikethrough and opacity if already requested
        if (item.isRequested) {
            console.log(`Row ${index} is already requested - adding strikethrough`);
            tr.style.textDecoration = 'line-through';
            tr.style.opacity = '0.6';
        }
        
        // Highlight the first row (oldest container by FIFO) in green - AFTER innerHTML is set
        if (index === 0) {
            console.log(`\n*** STYLING FIRST ROW (index ${index}) ***`);
            console.log('Before styling - tr.style.backgroundColor:', tr.style.backgroundColor);
            
            try {
                // Add unique identifiers for the first row (keep original ID)
                tr.setAttribute('data-first-row', 'true');
                tr.setAttribute('data-row-index', '0');
                tr.classList.add('oldest-container', 'first-container-row');
                // DON'T change the ID - keep it as `row-${item.Serial_No}` for handleRequest
                
                // SUPER AGGRESSIVE STYLING - Multiple approaches
                const greenStyle = 'background-color: #d4edda !important; border-left: 4px solid #28a745 !important; border: 2px solid #28a745 !important;';
                
                // Method 1: Direct style property
                tr.style.cssText = greenStyle;
                
                // Method 2: setAttribute with !important
                tr.setAttribute('style', greenStyle);
                
                // Method 3: Individual style properties
                tr.style.setProperty('background-color', '#d4edda', 'important');
                tr.style.setProperty('border-left', '4px solid #28a745', 'important');
                tr.style.setProperty('border', '2px solid #28a745', 'important');
                
                console.log('After styling attempts - tr.style.backgroundColor:', tr.style.backgroundColor);
                console.log('After styling attempts - tr.style.cssText:', tr.style.cssText);
                
                // Style all cells with EXTREME prejudice
                const cells = tr.querySelectorAll('td');
                console.log(`Found ${cells.length} cells in first row`);
                
                cells.forEach((cell, cellIndex) => {
                    console.log(`Aggressively styling cell ${cellIndex}`);
                    
                    // Multiple styling approaches for cells too
                    cell.style.cssText = 'background-color: #d4edda !important; color: #000 !important;';
                    cell.setAttribute('style', 'background-color: #d4edda !important; color: #000 !important;');
                    cell.style.setProperty('background-color', '#d4edda', 'important');
                    cell.classList.add('first-row-cell');
                    cell.setAttribute('data-first-row-cell', 'true');
                    
                    console.log(`Cell ${cellIndex} final backgroundColor:`, cell.style.backgroundColor);
                });
                
            } catch (error) {
                console.error('ERROR in first row styling:', error);
            }
            
            console.log('*** FIRST ROW STYLING COMPLETE ***\n');
        } else if (index % 2 === 1) {
            console.log(`Row ${index} - adding alternate row styling`);
            // Add manual striping for other rows
            tr.style.backgroundColor = '#f8f9fa';
        }
        
        tbody.appendChild(tr);
        console.log(`Row ${index} appended to tbody`);
        
        // Double-check styling after appending
        if (index === 0) {
            console.log(`\n*** POST-APPEND CHECK FOR FIRST ROW ***`);
            console.log('After appendChild - tr.style.backgroundColor:', tr.style.backgroundColor);
            console.log('After appendChild - computed style:', window.getComputedStyle(tr).backgroundColor);
            console.log('*** POST-APPEND CHECK COMPLETE ***\n');
        }
    });
    
    table.appendChild(thead);
    table.appendChild(tbody);
    containersTable.appendChild(table);
    
    console.log('Table structure complete');
    
    // Start persistent monitoring of first row styling
    startFirstRowMonitoring();
    
    console.log('=== updateContainersTable END ===\n');
}

// Function to update containers table
function updateContainersTable(data) {
    console.log('=== updateContainersTable START ===');
    console.log('updateContainersTable called with data:', data);
    console.log('Data length:', data.length);
    
    const containersTable = document.getElementById('containers-table');
    console.log('containersTable element found:', !!containersTable);
    
    // Clear existing content
    containersTable.innerHTML = '';
    console.log('containersTable cleared');
    
    // Create table
    const table = document.createElement('table');
    table.className = 'table table-hover mt-5'; // Removed table-striped to avoid conflicts
    console.log('Table created with classes:', table.className);
    
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
    console.log('Table header created');
    
    // Create table body
    const tbody = document.createElement('tbody');
    console.log('Table body created');
    
    data.forEach((item, index) => {
        console.log(`\n--- Processing row ${index} ---`);
        console.log(`Row ${index} data:`, item);
        
        const tr = document.createElement('tr');
        tr.id = `row-${item.Serial_No}`; // Add unique ID to each row
        console.log(`Created tr element with ID: ${tr.id}`);
        
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
        console.log(`Row ${index} innerHTML set`);
        
        // Add strikethrough and opacity if already requested
        if (item.isRequested) {
            console.log(`Row ${index} is already requested - adding strikethrough`);
            tr.style.textDecoration = 'line-through';
            tr.style.opacity = '0.6';
        }
        
        // Highlight the first row (oldest container by FIFO) in green - AFTER innerHTML is set
        if (index === 0) {
            console.log(`\n*** STYLING FIRST ROW (index ${index}) ***`);
            console.log('Before styling - tr.style.backgroundColor:', tr.style.backgroundColor);
            
            try {
                // Add unique identifiers for the first row (keep original ID)
                tr.setAttribute('data-first-row', 'true');
                tr.setAttribute('data-row-index', '0');
                tr.classList.add('oldest-container', 'first-container-row');
                // DON'T change the ID - keep it as `row-${item.Serial_No}` for handleRequest
                
                // SUPER AGGRESSIVE STYLING - Multiple approaches
                const greenStyle = 'background-color: #d4edda !important; border-left: 4px solid #28a745 !important; border: 2px solid #28a745 !important;';
                
                // Method 1: Direct style property
                tr.style.cssText = greenStyle;
                
                // Method 2: setAttribute with !important
                tr.setAttribute('style', greenStyle);
                
                // Method 3: Individual style properties
                tr.style.setProperty('background-color', '#d4edda', 'important');
                tr.style.setProperty('border-left', '4px solid #28a745', 'important');
                tr.style.setProperty('border', '2px solid #28a745', 'important');
                
                console.log('After styling attempts - tr.style.backgroundColor:', tr.style.backgroundColor);
                console.log('After styling attempts - tr.style.cssText:', tr.style.cssText);
                
                // Style all cells with EXTREME prejudice
                const cells = tr.querySelectorAll('td');
                console.log(`Found ${cells.length} cells in first row`);
                
                cells.forEach((cell, cellIndex) => {
                    console.log(`Aggressively styling cell ${cellIndex}`);
                    
                    // Multiple styling approaches for cells too
                    cell.style.cssText = 'background-color: #d4edda !important; color: #000 !important;';
                    cell.setAttribute('style', 'background-color: #d4edda !important; color: #000 !important;');
                    cell.style.setProperty('background-color', '#d4edda', 'important');
                    cell.classList.add('first-row-cell');
                    cell.setAttribute('data-first-row-cell', 'true');
                    
                    console.log(`Cell ${cellIndex} final backgroundColor:`, cell.style.backgroundColor);
                });
                
            } catch (error) {
                console.error('ERROR in first row styling:', error);
            }
            
            console.log('*** FIRST ROW STYLING COMPLETE ***\n');
        } else if (index % 2 === 1) {
            console.log(`Row ${index} - adding alternate row styling`);
            // Add manual striping for other rows
            tr.style.backgroundColor = '#f8f9fa';
        }
        
        tbody.appendChild(tr);
        console.log(`Row ${index} appended to tbody`);
        
        // Double-check styling after appending
        if (index === 0) {
            console.log(`\n*** POST-APPEND CHECK FOR FIRST ROW ***`);
            console.log('After appendChild - tr.style.backgroundColor:', tr.style.backgroundColor);
            console.log('After appendChild - computed style:', window.getComputedStyle(tr).backgroundColor);
            console.log('*** POST-APPEND CHECK COMPLETE ***\n');
        }
    });
    
    table.appendChild(thead);
    table.appendChild(tbody);
    containersTable.appendChild(table);
    
    console.log('Table structure complete');
    
    // Start persistent monitoring of first row styling
    startFirstRowMonitoring();
    
    console.log('=== updateContainersTable END ===\n');
}

// Function to handle request button click
async function handleRequest(serialNo, partNo, button) {
    console.log('\n🚀 HANDLE REQUEST CALLED');
    console.log('- serialNo:', serialNo);
    console.log('- partNo:', partNo);
    console.log('- button:', button);
    
    // Get row element for later use
    const row = document.getElementById(`row-${serialNo}`);
    console.log('- row element found:', !!row);
    console.log('- row ID searched:', `row-${serialNo}`);
    
    if (!row) {
        console.error('❌ Row element not found!');
        alert('Error: Could not find container row');
        return;
    }
    
    try {
        const workcenter = document.getElementById('Workcenter-input').value;
        const revision = document.getElementById('shipper-number-input').value;
        
        console.log('- workcenter:', workcenter);
        console.log('- revision:', revision);
        
        // VALIDATION FIRST - Don't change anything if validation fails
        if (!workcenter) {
            console.log('❌ Validation failed: No workcenter entered');
            alert('Please enter a workcenter');
            return; // Exit without changing button or row state
        }
        
        console.log('✅ Validation passed - proceeding with request');
        
        // NOW that validation passed, update button and row state
        button.disabled = true;
        button.textContent = 'Requested';
        button.className = 'btn btn-secondary btn-sm';
        
        // Add strikethrough to the row
        row.style.textDecoration = 'line-through';
        row.style.opacity = '0.6';
        console.log('- button and row styling applied after validation');
        
        // SAFE CELL SELECTION WITH DEBUGGING
        let location = '';
        let quantity = '';
        
        if (row) {
            const locationCell = row.querySelector('td:nth-child(5)');
            const quantityCell = row.querySelector('td:nth-child(4)');
            
            console.log('- locationCell found:', !!locationCell);
            console.log('- quantityCell found:', !!quantityCell);
            
            if (locationCell) {
                location = locationCell.textContent;
                console.log('- location:', location);
            } else {
                console.error('❌ Location cell not found!');
            }
            
            if (quantityCell) {
                quantity = quantityCell.textContent;
                console.log('- quantity:', quantity);
            } else {
                console.error('❌ Quantity cell not found!');
            }
        }
        
        const requestBody = {
            workcenter: workcenter,
            revision: revision,
            location: location,
            quantity: quantity,
            req_time: new Date().toISOString()
        };
        
        console.log('- request body:', requestBody);
        
        // VALIDATION: Check if we have essential data
        if (!location || !quantity) {
            console.warn('⚠️ WARNING: Missing location or quantity data!');
            console.warn('- This may prevent proper database storage');
        } else {
            console.log('✅ Complete request data captured');
        }
        
        const response = await fetch(`/part/${partNo}/${serialNo}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });
        
        console.log('- API response status:', response.status);
        console.log('- API response statusText:', response.statusText);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.log('- API error response:', errorText);
            throw new Error(`Request failed: ${response.status} ${response.statusText}`);
        }
        
        const responseText = await response.text();
        let responseData;
        try {
            responseData = JSON.parse(responseText);
        } catch (jsonError) {
            console.error('Failed to parse JSON response:', jsonError);
            console.error('Response text:', responseText);
            throw new Error('Invalid JSON response from server');
        }
        console.log('- API success response:', responseData);
        
        // Optional: Show success message
        const successAlert = document.createElement('div');
        successAlert.className = 'alert alert-success alert-dismissible fade show mt-3';
        successAlert.innerHTML = `
            Container ${serialNo} requested successfully
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        document.getElementById('containers-table').insertBefore(successAlert, document.getElementById('containers-table').firstChild);
        
        console.log('✅ Request completed successfully');
        
    } catch (error) {
        console.error('❌ ERROR in handleRequest:', error);
        console.error('- Error message:', error.message);
        console.error('- Error stack:', error.stack);
        
        // Revert the button and row state if API request fails AFTER validation passed
        console.log('🔄 Reverting button and row state due to API error');
        button.disabled = false;
        button.textContent = 'Request';
        button.className = 'btn btn-primary btn-sm';
        if (row) {
            row.style.textDecoration = 'none';
            row.style.opacity = '1';
        }
        console.log('✅ Button and row state reverted');
        
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

document.getElementById('serial-no-input').addEventListener('keydown', async (e) => {
    enterKeyPressed(e);
});

async function enterKeyPressed(e) {
    console.log('\n🔥 ENTER KEY EVENT FIRED!');
    console.log('- Key pressed:', e.key);
    console.log('- Event target:', e.target.id);
    
    // Get current values
    const serialNo = document.getElementById('serial-no-input').value;
    const partNo = document.getElementById('part-no-input').value;
    console.log('- Serial number value:', serialNo);
    console.log('- Part number value:', partNo);
    
    // Skip processing if Enter wasn't pressed
    if (e.key !== "Enter") {
        console.log('⏭️ Not Enter key, skipping');
        return;
    }
    
    console.log("---------------------------------------------------------------------");
    
    // Priority 1: If serial number exists, search by serial number (regardless of which field triggered)
    if (serialNo) {
        console.log('✅ Serial number exists - calling fetchContainerInfo');
        const data = await fetchContainerInfo(serialNo);
        return; // Exit early - don't process part number
    }
    
    // Priority 2: If part number exists (and no serial number), search by part number
    if (partNo) {
        console.log('✅ Part number exists - calling fetchContainers');
        const data = await fetchContainers(partNo);
        return; // Exit early
    }
    
    // Priority 3: If neither exists, show message (only if Enter was pressed in search-related fields)
    const searchFields = ['part-no-input', 'serial-no-input'];
    if (searchFields.includes(e.target.id)) {
        console.log("❌ No part number or serial number entered");
        clearContainersTable();
        displayMessage("Please enter a part number or serial number");
    } else {
        console.log('⏭️ Enter pressed in non-search field, no action needed');
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
            }).then(async response => {
                const responseText = await response.text();
                try {
                    return JSON.parse(responseText);
                } catch (jsonError) {
                    console.error('Failed to parse JSON response:', jsonError);
                    console.error('Response text:', responseText);
                    throw new Error('Invalid JSON response from server');
                }
            }).then(data => {
                console.log("--------------------------------");
                console.log(data);
                let table = '<table style="width: 100%;" display="block">';
                table += '<thead><tr><th>No</th><th>Serial No</th><th>Part No</th><th>Revision</th><th>Quantity</th><th>Location</th><th>Add Date</th></tr></thead>';
                table += '<tbody>';
                let container = null;
                let rowIndex = 0; // Track the actual row index for display
                data.dataframe.forEach((row, index) => {
                    // Check if the location is in our production locations list
                    // const inValidLocation = prodLocations.includes(row.Location);
                    // console.log(`Location ${row.Location} is ${inValidLocation ? 'invalid' : 'valid'}`);
                    
                    // // You can use this information to style the row or add validation
                    // const rowStyle = inValidLocation ? 'color: red' : '';

                    if(!prodLocations.includes(row.Location)){
                        // Add green highlighting for the first row (oldest container by FIFO)
                        const isFirstRow = rowIndex === 0;
                        const rowStyle = isFirstRow ? 'background-color: #d4edda; border-left: 4px solid #28a745;' : '';
                        
                        table += `<tr class="clickable-row ${isFirstRow ? 'oldest-container' : ''}" style="cursor: pointer; ${rowStyle}">
                            <td>${rowIndex + 1}</td>
                            <td>${row.Serial_No}</td>
                            <td>${row.Part_No}</td>
                            <td>${row.Revision}</td>
                            <td>${row.Quantity}</td>
                            <td>${row.Location}</td>
                            <td>${row.Add_Date}</td>
                        </tr>`;
                        
                        rowIndex++; // Increment only for displayed rows
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
                        }).then(async response => {
                            const responseText = await response.text();
                            try {
                                return JSON.parse(responseText);
                            } catch (jsonError) {
                                console.error('Failed to parse JSON response:', jsonError);
                                console.error('Response text:', responseText);
                                throw new Error('Invalid JSON response from server');
                            }
                        }).then(data => {
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

// PERSISTENT FIRST ROW GREEN STYLING MONITOR
let firstRowMonitor = null;

function startFirstRowMonitoring() {
    console.log('🟢 Starting persistent first row monitoring');
    
    // Clear any existing monitor
    if (firstRowMonitor) {
        clearInterval(firstRowMonitor);
    }
    
    // Function to aggressively ensure first row is green
    function enforceFirstRowGreen() {
        try {
            const containersTable = document.getElementById('containers-table');
            if (!containersTable) return;
            
            const firstRow = containersTable.querySelector('tbody tr:first-child, tr[data-first-row="true"], .first-container-row, .oldest-container');
            
            if (firstRow) {
                const currentBgColor = window.getComputedStyle(firstRow).backgroundColor;
                const isGreen = currentBgColor.includes('212, 237, 218') || currentBgColor.includes('#d4edda');
                
                if (!isGreen) {
                    console.log('🔴 First row lost green color, reapplying!');
                    console.log('Current background:', currentBgColor);
                    
                    // NUCLEAR OPTION - Multiple aggressive styling methods
                    const superGreenStyle = 'background-color: #d4edda !important; border-left: 4px solid #28a745 !important; border: 2px solid #28a745 !important;';
                    
                    firstRow.style.cssText = superGreenStyle;
                    firstRow.setAttribute('style', superGreenStyle);
                    firstRow.style.setProperty('background-color', '#d4edda', 'important');
                    firstRow.style.setProperty('border-left', '4px solid #28a745', 'important');
                    firstRow.style.setProperty('border', '2px solid #28a745', 'important');
                    
                    // Also force all cells
                    const cells = firstRow.querySelectorAll('td');
                    cells.forEach(cell => {
                        cell.style.cssText = 'background-color: #d4edda !important; color: #000 !important;';
                        cell.setAttribute('style', 'background-color: #d4edda !important; color: #000 !important;');
                        cell.style.setProperty('background-color', '#d4edda', 'important');
                    });
                    
                    console.log('🟢 First row styling reapplied');
                }
            }
        } catch (error) {
            console.error('Error in first row monitoring:', error);
        }
    }
    
    // Run immediately
    setTimeout(enforceFirstRowGreen, 100);
    
    // Then monitor every 500ms
    firstRowMonitor = setInterval(enforceFirstRowGreen, 500);
    
    console.log('🟢 First row monitor started');
}
