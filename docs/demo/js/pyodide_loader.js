// js/pyodide.js

// Ymery version - updated by build process
const YMERY_VERSION = "0.0.68";

async function load_pyodide_imgui_render() {
    console.log('Loading load_pyodide_imgui_render.py');
    try {
        const response = await fetch('py_imgui_render/pyodide_imgui_render.py');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const pythonCode = await response.text();

        // Execute the Python code
        await pyodide.runPythonAsync(pythonCode);
        // console.log('Pyodide ImGui render code loaded and executed successfully.');
    } catch (error) {
        console.error('Error in load_pyodide_imgui_render:', error);
        displayError('Failed during init (load_pyodide_imgui_render): see console for details.');
    }
}


// Debug function to test that SDL is correctly linked
// see https://github.com/pyodide/pyodide/issues/5248
async function loadPyodideAndPackages_test_daft_lib() {
    showLoadingModal();
    updateProgress(0, 'Loading Pyodide...');
    pyodide = await loadPyodide();
    const pythonVersion = pyodide.runPython("import sys; sys.version");
    updateProgress(7, 'Pyodide loaded.');
    console.log("Python version:", pythonVersion);
    await pyodide.loadPackage("micropip");
    await pyodide.loadPackage("micropip"); // firefox needs this to be loaded twice...
    updateProgress(10, 'micropip loaded.');

    // SDL support in Pyodide is experimental. The flag is used to bypass certain issues.
    pyodide._api._skip_unwind_fatal_error = true;

    // Determine the base URL dynamically
    const baseUrl = `${window.location.origin}${window.location.pathname}`;
    console.log('Base URL:', baseUrl);

    await pyodide.runPythonAsync(`
print("Before import micropip")
import micropip;
print("Before micropip.install")
await micropip.install('daft-lib')

print("Before import daft_lib")
import daft_lib
print("Before daft_lib.dummy_sdl_call")
daft_lib.dummy_sdl_call()
print("After daft_lib.dummy_sdl_call")
            `);

}


// Initialize Pyodide and load packages with progress updates
async function loadPyodideAndPackages() {
    try {
        showLoadingModal();
        updateProgress(0, 'Loading Pyodide...');

        console.log(`Target ymery version: ${YMERY_VERSION}`);

        pyodide = await loadPyodide();
        const pythonVersion = pyodide.runPython("import sys; sys.version");
        updateProgress(7, 'Pyodide loaded.');
        console.log("Python version:", pythonVersion);
        await pyodide.loadPackage("micropip");
        await pyodide.loadPackage("micropip"); // firefox needs this to be loaded twice...
        updateProgress(10, 'micropip loaded.');

        // SDL support in Pyodide is experimental. The flag is used to bypass certain issues.
        pyodide._api._skip_unwind_fatal_error = true;

        // List of packages to install
        const packages = [
            // Core Python packages from PyPI
            // ------------------------------
            'numpy',
            'pyyaml',
            'click',
            'httpx',
            'munch',
            'pillow',
            'typing_extensions',
            'matplotlib',

            // ImGui Bundle (Pyodide-compatible, installed via micropip)
            // ----------------------------------------------------------
            'imgui_bundle',

            // Ymery (from PyPI) - pinned to version from build
            // -----------------
            `ymery==${YMERY_VERSION}`,
        ];

        const totalSteps = packages.length;
        let currentStep = 1;

        for (const pkg of packages) {
            updateProgress(10 + (currentStep / totalSteps) * 80, `Installing ${pkg}...`);
            console.log(`Installing ${pkg}...`);
            try {
                const installCode = pkg.startsWith('ymery')
                    ? `
import micropip
import sys
print(f"Python version: {sys.version}")
print(f"Installing ${pkg}...")
await micropip.install('${pkg}', keep_going=True, deps=True)
import ymery
print(f"ymery version: {ymery.__version__ if hasattr(ymery, '__version__') else 'unknown'}")
`
                    : `
import micropip
import sys
print(f"Installing ${pkg}...")
await micropip.install('${pkg}', keep_going=True, deps=True)
print(f"Successfully installed ${pkg}")
`;
                await pyodide.runPythonAsync(installCode);
                console.log(`${pkg} installed successfully.`);
            } catch (err) {
                console.error(`Failed to install ${pkg}:`, err);
                displayError(`Failed to install ${pkg}: ${err.message}`);
                throw err;
            }
            currentStep++;
        }

        updateProgress(100, 'All packages loaded.');
        // Optionally, add a slight delay before hiding the modal
        await new Promise(resolve => setTimeout(resolve, 500));
        hideLoadingModal();
        console.log('Pyodide and packages loaded.');
    } catch (error) {
        console.error('Error loading Pyodide or packages:', error);
        displayError('Failed to load Pyodide or install packages. See console for details.');
        hideLoadingModal();
    }
}

// Function to run ymery with aggregated YAML from editor
async function runEditorPythonCode() {
    if (!pyodide) {
        console.error('Pyodide not loaded yet');
        displayError('Pyodide is still loading. Please wait a moment and try again.');
        return;
    }

    if (!window.currentExample) {
        displayError('No example selected. Please select an example from the dropdown.');
        return;
    }

    const yamlContent = editor.getValue();
    const example = window.currentExample;

    // Clear previous errors before running new code
    clearError();

    try {
        // Redirect stdout and stderr
        pyodide.setStdout({
            batched: (s) => console.log(s),
        });
        pyodide.setStderr({
            batched: (s) => {
                // Filter out Python DEBUG log messages (e.g., from PIL)
                if (s.startsWith('DEBUG:')) {
                    console.log('[DEBUG]', s);
                    return;
                }
                console.error(s);
                displayError(s);
            },
        });

        // Write the edited aggregated YAML to Pyodide's virtual filesystem
        const fs = pyodide.FS;
        const tempDir = '/tmp/ymery_demo';
        fs.mkdirTree(tempDir);
        fs.writeFile(`${tempDir}/app.yaml`, yamlContent);

        // Run ymery with the aggregated YAML (no imports needed since everything is inline)
        const pythonCode = `
import sys
sys.argv = [
    'ymery',
    '--layouts-path', '${tempDir}',
    '--main', 'app'
]

from ymery.app import main
main(standalone_mode=False)
`;

        console.log('Running ymery with aggregated YAML from editor');
        await pyodide.runPythonAsync(pythonCode);

    } catch (err) {
        console.error('Caught PythonError:', err);
        displayError(err.toString());
    }
}
