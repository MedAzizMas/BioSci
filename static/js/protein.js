// Protein Alignment Page JavaScript
let currentResultId = null;

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('alignmentForm');
    const humanInput = document.getElementById('humanProtein');
    const bacteriaInput = document.getElementById('bacteriaProtein');

    // Example button handler
    document.querySelectorAll('.example-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            humanInput.value = btn.dataset.human;
            bacteriaInput.value = btn.dataset.bacteria;
            validateProtein('humanProtein', 'human');
            validateProtein('bacteriaProtein', 'bacteria');
        });
    });

    // Validate on blur
    humanInput.addEventListener('blur', () => validateProtein('humanProtein', 'human'));
    bacteriaInput.addEventListener('blur', () => validateProtein('bacteriaProtein', 'bacteria'));

    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const humanProtein = humanInput.value.trim();
        const bacteriaProtein = bacteriaInput.value.trim();
        const computeFunctional = document.getElementById('computeFunctional').checked;
        const useLLM = document.getElementById('useLLM').checked;

        // Hide previous results/errors
        document.getElementById('resultsPreview').style.display = 'none';
        document.getElementById('errorContainer').style.display = 'none';

        // Show progress
        document.getElementById('progressContainer').style.display = 'block';
        updateProgress(10, 'Validating protein IDs...');

        try {
            const response = await fetch('/api/protein/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    human_protein_id: humanProtein,
                    bact_protein_id: bacteriaProtein,
                    compute_functional: computeFunctional,
                    use_llm: useLLM
                })
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Analysis failed');
            }

            currentResultId = data.result_id;
            displayResults(data.results);

        } catch (error) {
            showError(error.message);
        } finally {
            document.getElementById('progressContainer').style.display = 'none';
        }
    });
});

async function validateProtein(inputId, organism) {
    const input = document.getElementById(inputId);
    const statusId = organism === 'human' ? 'humanStatus' : 'bacteriaStatus';
    const statusElement = document.getElementById(statusId);

    const proteinId = input.value.trim();
    if (!proteinId) {
        statusElement.textContent = '';
        return;
    }

    statusElement.textContent = 'Checking...';
    statusElement.className = 'status-text';

    try {
        const payload = {};
        payload[`${organism}_protein_id`] = proteinId;

        const response = await fetch('/api/protein/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (data.success && data.validation[organism]) {
            const validation = data.validation[organism];
            if (validation.exists) {
                statusElement.textContent = `✓ Found (${validation.num_chunks} chunks)`;
                statusElement.className = 'status-text success';
            } else {
                statusElement.textContent = `✗ ${validation.error}`;
                statusElement.className = 'status-text error';
            }
        }
    } catch (error) {
        statusElement.textContent = '✗ Validation failed';
        statusElement.className = 'status-text error';
    }
}

function updateProgress(percent, text) {
    document.getElementById('progressBar').style.width = `${percent}%`;
    document.getElementById('progressText').textContent = text;
}

function displayResults(results) {
    const summary = results.alignment_summary;
    const humanLen = results.input_sequences.human.length_aa;
    const bacteriaLen = results.input_sequences.bacteria.length_aa;

    const humanCoverage = ((summary.total_human_aa_aligned / humanLen) * 100).toFixed(1);
    const bacteriaCoverage = ((summary.total_bact_aa_aligned / bacteriaLen) * 100).toFixed(1);

    let summaryHTML = `
        <div class="stats-grid">
            <div class="stat-card">
                <span class="stat-value">${summary.filtered_alignments}</span>
                <span class="stat-label">High-Quality Alignments</span>
            </div>
            <div class="stat-card">
                <span class="stat-value">${humanCoverage}%</span>
                <span class="stat-label">Human Coverage</span>
            </div>
            <div class="stat-card">
                <span class="stat-value">${bacteriaCoverage}%</span>
                <span class="stat-label">Bacteria Coverage</span>
            </div>
            <div class="stat-card">
                <span class="stat-value">${summary.best_avg_similarity ? summary.best_avg_similarity.toFixed(3) : 'N/A'}</span>
                <span class="stat-label">Best Similarity</span>
            </div>
        </div>
    `;

    if (results.llm_analysis && !results.llm_analysis.error) {
        const llm = results.llm_analysis;
        summaryHTML += `
            <div class="interpretation-box" style="margin-top: 20px;">
                <h3>🤖 LLM Interpretation</h3>
                <p><strong>Relationship:</strong> ${llm.biological_interpretation.relationship_type.replace(/_/g, ' ')}</p>
                <p><strong>Confidence:</strong> ${llm.confidence_score}%</p>
                <p>${llm.biological_interpretation.evidence_summary}</p>
            </div>
        `;
    }

    document.getElementById('summaryContent').innerHTML = summaryHTML;
    document.getElementById('resultsPreview').style.display = 'block';
}

function showError(message) {
    document.getElementById('errorText').textContent = message;
    document.getElementById('errorContainer').style.display = 'block';
}

function viewFullResults() {
    if (currentResultId) {
        window.location.href = `/protein/results/${currentResultId}`;
    }
}

function downloadResults() {
    if (currentResultId) {
        window.location.href = `/api/protein/download/${currentResultId}`;
    }
}

// 3D Structure Viewer Functions
let viewer = null;
let isSpinning = false;

function view3DStructure(type) {
    const inputId = type === 'human' ? 'humanProtein' : 'bacteriaProtein';
    const proteinId = document.getElementById(inputId).value.trim();
    
    if (!proteinId) {
        alert('Please enter a protein ID first');
        return;
    }
    
    // Show modal
    const modal = document.getElementById('structureModal');
    modal.style.display = 'flex';
    
    // Update title
    const title = type === 'human' ? 'Human Protein Structure' : 'Bacterial Protein Structure';
    document.getElementById('modalTitle').textContent = title;
    
    // Show loading, hide others
    document.getElementById('structureLoading').style.display = 'flex';
    document.getElementById('structureError').style.display = 'none';
    document.getElementById('viewer3d').style.display = 'none';
    document.getElementById('structureInfo').style.display = 'none';
    
    // Fetch structure
    fetchAndDisplayStructure(proteinId);
}

async function fetchAndDisplayStructure(proteinId) {
    try {
        const response = await fetch(`/api/protein/structure/${encodeURIComponent(proteinId)}`);
        const data = await response.json();
        
        if (!data.success) {
            showStructureError(data.error || 'Structure not found');
            return;
        }
        
        // Hide loading, show viewer
        document.getElementById('structureLoading').style.display = 'none';
        document.getElementById('viewer3d').style.display = 'block';
        document.getElementById('structureInfo').style.display = 'block';
        
        // Update info
        document.getElementById('infoUniprotId').textContent = data.uniprot_id;
        document.getElementById('infoSource').textContent = data.source + (data.version ? ` v${data.version}` : '');
        
        // Update protein name and organism if available
        const nameEl = document.getElementById('infoProteinName');
        const organismEl = document.getElementById('infoOrganism');
        const plddtEl = document.getElementById('infoPlddtScore');
        
        if (nameEl && data.protein_name) nameEl.textContent = data.protein_name;
        if (organismEl && data.organism) organismEl.textContent = data.organism;
        if (plddtEl && data.plddt_score) plddtEl.textContent = data.plddt_score.toFixed(1);
        
        // Initialize 3Dmol viewer
        initViewer(data.pdb_data);
        
    } catch (error) {
        showStructureError('Failed to fetch structure: ' + error.message);
    }
}

function initViewer(pdbData) {
    const viewerDiv = document.getElementById('viewer3d');
    
    // Clear previous viewer
    viewerDiv.innerHTML = '';
    
    // Create new viewer
    viewer = $3Dmol.createViewer(viewerDiv, {
        backgroundColor: '#0d0d1a'
    });
    
    // Add model
    viewer.addModel(pdbData, 'pdb');
    
    // Color by pLDDT (B-factor in AlphaFold PDB files)
    // AlphaFold stores pLDDT in B-factor column
    viewer.setStyle({}, {
        cartoon: {
            colorfunc: function(atom) {
                // pLDDT is stored in b-factor
                const plddt = atom.b;
                if (plddt > 90) return '#0053D6';      // Very high - blue
                if (plddt > 70) return '#65CBF3';      // High - light blue
                if (plddt > 50) return '#FFDB13';      // Low - yellow
                return '#FF7D45';                       // Very low - orange
            }
        }
    });
    
    // Zoom to fit
    viewer.zoomTo();
    viewer.render();
}

function showStructureError(message) {
    document.getElementById('structureLoading').style.display = 'none';
    document.getElementById('structureError').style.display = 'flex';
    document.getElementById('structureErrorText').textContent = message;
}

function closeModal() {
    document.getElementById('structureModal').style.display = 'none';
    if (viewer) {
        viewer.spin(false);
        isSpinning = false;
    }
}

function resetView() {
    if (viewer) {
        viewer.zoomTo();
        viewer.render();
    }
}

function toggleSpin() {
    if (viewer) {
        isSpinning = !isSpinning;
        viewer.spin(isSpinning ? 'y' : false);
    }
}

// Close modal on escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeModal();
    }
});

// Close modal on overlay click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        closeModal();
    }
});
