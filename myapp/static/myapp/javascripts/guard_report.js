
  // Date & Time (unchanged)
  function updateDateTime() {
    const now = new Date();
    const dateOptions = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    const timeOptions = { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true };
    document.getElementById('currentDate').textContent = now.toLocaleDateString('en-US', dateOptions);
    document.getElementById('currentTime').textContent = now.toLocaleTimeString('en-US', timeOptions);
  }
  updateDateTime();
  setInterval(updateDateTime, 1000);

  // --- Minimal guardrail for the date inputs (HTML-side only) ---
  (function () {
    const form  = document.getElementById('reportForm');
    if (!form) return;

    const start = form.querySelector('input[name="start_date"]');
    const end   = form.querySelector('input[name="end_date"]');
    const guard = form.querySelector('select[name="guard_name"]');

    // Use server-provided bound if present; otherwise fallback to client "today"
    const floor = "2020-01-01";
    const maxFromTemplate = "{{ today|date:'Y-m-d' }}";   // will be empty if not passed
    const today = (/^\d{4}-\d{2}-\d{2}$/.test(maxFromTemplate))
      ? maxFromTemplate
      : new Date().toISOString().slice(0,10);

    // Ensure min/max attributes exist even if template vars are missing
    [start, end].forEach(inp => {
      if (!inp) return;
      if (!inp.min) inp.min = floor;
      if (!inp.max) inp.max = today;
    });

    function clamp(input) {
      if (!input || !input.value) return;
      if (input.value < input.min) input.value = input.min;
      if (input.value > input.max) input.value = input.max;
    }

    [start, end].forEach(inp => inp && inp.addEventListener('change', () => clamp(inp)));

    form.addEventListener('submit', function (e) {
      clamp(start); clamp(end);
      const s  = start && start.value ? start.value : floor;
      const ed = end   && end.value   ? end.value   : today;

      if (s > ed) {
        e.preventDefault();
        alert("Start Date cannot be after End Date.");
        return;
      }
    });
  })();
