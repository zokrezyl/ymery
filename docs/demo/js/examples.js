// js/examples.js
// Handles loading aggregated YAML demos from the ymery package

// Load initial example
async function loadInitialExample() {
    // Load the first example by default
    const examples = await fetchExampleMetadata();
    if (examples.length > 0) {
        await loadExample(examples[0]);
    } else {
        // Fallback YAML
        editor.setValue(`# No examples available
# Add demos to examples.json
app:
  widget: builtin.text
  data: demo-data

data:
  demo-data:
    metadata:
      label: "Hello from Ymery!"
`);
    }
}

// Fetch example metadata from JSON
async function fetchExampleMetadata() {
    try {
        const response = await fetch('examples/examples.json');
        const data = await response.json();
        return data.examples;
    } catch (error) {
        console.error('Error fetching example metadata:', error);
        displayError('Failed to fetch example metadata. See console for details.');
        return [];
    }
}

// Load aggregated YAML from the ymery package
async function loadExample(example) {
    try {
        // Wait for Pyodide to be ready
        if (!window.pyodide) {
            displayError('Pyodide is still loading. Please wait...');
            return;
        }

        console.log(`Loading aggregated example: ${example.aggregated_file}`);

        // Read the aggregated YAML file from the ymery package
        const yamlContent = await window.pyodide.runPythonAsync(`
import importlib.resources
import ymery.demo_aggregated

# Read the aggregated YAML file
yaml_path = importlib.resources.files('ymery.demo_aggregated') / '${example.aggregated_file}'
yaml_path.read_text()
`);

        // Set editor content
        editor.setValue(yamlContent);

        // Store the example metadata for running
        window.currentExample = example;

        clearError();
    } catch (error) {
        console.error('Error loading example:', error);
        displayError(`Failed to load example from package: ${error.message}`);
    }
}

// Populate example selector dropdown
async function populateExampleSelector() {
    const examplesList = await fetchExampleMetadata();

    const exampleSelector = document.getElementById('example-selector');
    exampleSelector.innerHTML = '<option value="">-- Select an Example --</option>';

    examplesList.forEach((example, index) => {
        const option = document.createElement('option');
        option.value = index;
        option.textContent = example.label;
        if (example.description) {
            option.title = example.description;
        }
        exampleSelector.appendChild(option);
    });

    // Set first example as selected
    if (examplesList.length > 0) {
        exampleSelector.selectedIndex = 1; // Index 0 is "-- Select --"
    }
}

// Initialize example selector after Pyodide loads
async function initializeExampleSelector() {
    // Populate selector
    await populateExampleSelector();

    // Load initial example
    await loadInitialExample();

    // Add event listener for example selector changes
    const exampleSelector = document.getElementById('example-selector');
    const examplesList = await fetchExampleMetadata();

    exampleSelector.addEventListener('change', async (event) => {
        const selectedIndex = event.target.value;
        if (selectedIndex !== '') {
            const example = examplesList[parseInt(selectedIndex)];
            await loadExample(example);
        }
    });
}
