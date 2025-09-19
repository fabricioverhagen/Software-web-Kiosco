// Script genérico para filtrar tablas por nombre/texto y fecha

/**
 * Inicializa filtros para una tabla.
 * options: { nameInputId, dateInputId, tableSelector, dateColumnIndex }
 */
function initTableFilters(options) {
    const nameInput = document.getElementById(options.nameInputId);
    const dateInput = document.getElementById(options.dateInputId);
    const table = document.querySelector(options.tableSelector);
    const dateCol = options.dateColumnIndex || 1; // por defecto segunda columna

    if (!table) return;

    function applyFilters() {
        const nameVal = nameInput ? nameInput.value.trim().toLowerCase() : '';
        const dateVal = dateInput ? dateInput.value : '';

        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            let textMatch = true;
            let dateMatch = true;

            if (nameVal) {
                const rowText = row.textContent.toLowerCase();
                textMatch = rowText.includes(nameVal);
            }

            if (dateVal) {
                const cells = row.querySelectorAll('td');
                if (cells.length > dateCol) {
                    const cellDate = cells[dateCol].textContent.trim();
                    // Intentar normalizar la fecha de la celda a YYYY-MM-DD; si no coincide, hacer contains
                    if (cellDate.includes(dateVal) || cellDate.endsWith(dateVal) || cellDate.startsWith(dateVal)) {
                        dateMatch = true;
                    } else {
                        // Comparación más laxa: eliminar espacios y comparar
                        dateMatch = cellDate.indexOf(dateVal) !== -1;
                    }
                } else {
                    dateMatch = false;
                }
            }

            if (textMatch && dateMatch) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }

    if (nameInput) nameInput.addEventListener('input', applyFilters);
    if (dateInput) dateInput.addEventListener('change', applyFilters);
}

// Auto-inicialización para las tablas conocidas
document.addEventListener('DOMContentLoaded', function() {
    try {
        initTableFilters({ nameInputId: 'productos_filter_name', dateInputId: 'productos_filter_date', tableSelector: '.table', dateColumnIndex: 4 });
    } catch (e) {}
    try {
        initTableFilters({ nameInputId: 'clientes_filter_name', dateInputId: 'clientes_filter_date', tableSelector: '.table', dateColumnIndex: 1 });
    } catch (e) {}
    try {
        initTableFilters({ nameInputId: 'facturas_filter_name', dateInputId: 'facturas_filter_date', tableSelector: '.table', dateColumnIndex: 1 });
    } catch (e) {}
});