// 3D Structure Viewer for Results Page
let viewer = null;
let isSpinning = false;

function view3DStructure(proteinId, label) {
    // Show modal
    const modal = document.getElementById('structureModal');
    modal.style.display = 'flex';
    
    // Update title
    document.getElementById('modalTitle').textContent = label + ' Protein Structure';
    
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
    viewerDiv.innerHTML = '';
    
    viewer = $3Dmol.createViewer(viewerDiv, {
        backgroundColor: '#0d0d1a'
    });
    
    viewer.addModel(pdbData, 'pdb');
    
    // Color by pLDDT confidence
    viewer.setStyle({}, {
        cartoon: {
            colorfunc: function(atom) {
                const plddt = atom.b;
                if (plddt > 90) return '#0053D6';
                if (plddt > 70) return '#65CBF3';
                if (plddt > 50) return '#FFDB13';
                return '#FF7D45';
            }
        }
    });
    
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

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});

document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) closeModal();
});
