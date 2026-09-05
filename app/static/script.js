// ==========================================
// ELEMENTS
// ==========================================

const progressBar =
    document.getElementById(
        "progressBar"
    );

const progressPercent =
    document.getElementById(
        "progressPercent"
    );

let progressInterval = null;

const imageInput =
    document.getElementById("imageInput");

const dropZone =
    document.getElementById("dropZone");

const imagePreview =
    document.getElementById("imagePreview");

const resultProductImage =
    document.getElementById(
        "resultProductImage"
    );

const previewContainer =
    document.getElementById(
        "previewContainer"
    );

const emptyPreview =
    document.getElementById(
        "emptyPreview"
    );

const analyzeButton =
    document.getElementById(
        "analyzeButton"
    );

const selectedFileName =
    document.getElementById(
        "selectedFileName"
    );

const loadingSection =
    document.getElementById(
        "loadingSection"
    );

const resultsSection =
    document.getElementById(
        "resultsSection"
    );

const scannerSection =
    document.getElementById(
        "scannerSection"
    );

const newScanButton =
    document.getElementById(
        "newScanButton"
    );

const elapsedTime =
    document.getElementById(
        "elapsedTime"
    );
    


let selectedFile = null;
let previewURL = null;


let timerInterval = null;

function startProgress() {

    let progress = 0;

    progressBar.style.width =
        "0%";

    progressPercent.textContent =
        "0%";

    progressInterval =
        setInterval(
            () => {

                if (progress < 30) {
                    progress += 5;
                }

                else if (progress < 60) {
                    progress += 3;
                }

                else if (progress < 85) {
                    progress += 2;
                }

                else if (progress < 95) {
                    progress += 1;
                }

                progress =
                    Math.min(
                        progress,
                        95
                    );

                updateProgress(
                    progress
                );

            },
            1000
        );
}


function updateProgress(value) {

    const rounded =
        Math.round(value);

    progressBar.style.width =
        `${rounded}%`;

    progressPercent.textContent =
        `${rounded}%`;

    updateAnalysisStep(
        rounded
    );
}


function finishProgress() {

    if (progressInterval) {

        clearInterval(
            progressInterval
        );

        progressInterval = null;
    }

    updateProgress(
        100
    );
}
// ==========================================
// FILE SELECTION
// ==========================================

imageInput.addEventListener(
    "change",
    () => {

        if (imageInput.files.length > 0) {
            setSelectedFile(
                imageInput.files[0]
            );
        }

    }
);

function updateAnalysisStep(progress) {

    const steps =
        document.querySelectorAll(
            ".analysis-step"
        );


    steps.forEach(
        step =>
            step.classList.remove(
                "active"
            )
    );


    if (progress < 40) {

        steps[0]?.classList.add(
            "active"
        );

        document.getElementById(
            "loadingTitle"
        ).textContent =
            "Reading product label...";

        document.getElementById(
            "loadingMessage"
        ).textContent =
            "PaddleOCR is detecting and reading text from the package.";

    }
    else if (progress < 70) {

        steps[1]?.classList.add(
            "active"
        );

        document.getElementById(
            "loadingTitle"
        ).textContent =
            "Extracting declarations...";

        document.getElementById(
            "loadingMessage"
        ).textContent =
            "Detected text is being converted into structured product fields.";

    }
    else if (progress < 95) {

        steps[2]?.classList.add(
            "active"
        );

        document.getElementById(
            "loadingTitle"
        ).textContent =
            "Checking compliance...";

        document.getElementById(
            "loadingMessage"
        ).textContent =
            "Extracted declarations are being checked against compliance rules.";

    }
    else {

        steps[3]?.classList.add(
            "active"
        );

        document.getElementById(
            "loadingTitle"
        ).textContent =
            "Preparing report...";

        document.getElementById(
            "loadingMessage"
        ).textContent =
            "Final compliance results are being prepared.";
    }
}

// ==========================================
// DRAG AND DROP
// ==========================================

dropZone.addEventListener(
    "dragover",
    event => {

        event.preventDefault();

        dropZone.classList.add(
            "drag-active"
        );
    }
);


dropZone.addEventListener(
    "dragleave",
    () => {

        dropZone.classList.remove(
            "drag-active"
        );
    }
);


dropZone.addEventListener(
    "drop",
    event => {

        event.preventDefault();

        dropZone.classList.remove(
            "drag-active"
        );

        const file =
            event.dataTransfer.files[0];

        if (
            file &&
            file.type.startsWith(
                "image/"
            )
        ) {

            setSelectedFile(
                file
            );
        }

    }
);


function setSelectedFile(file) {

    selectedFile = file;

    if (previewURL) {
        URL.revokeObjectURL(
            previewURL
        );
    }

    previewURL =
        URL.createObjectURL(
            file
        );

    imagePreview.src =
        previewURL;

    resultProductImage.src =
        previewURL;

    emptyPreview.classList.add(
        "hidden"
    );

    previewContainer.classList.remove(
        "hidden"
    );

    selectedFileName.textContent =
        file.name;

    analyzeButton.disabled =
        false;
}


// ==========================================
// ANALYZE
// ==========================================

analyzeButton.addEventListener(
    "click",
    analyzeProduct
);


async function analyzeProduct() {

    if (!selectedFile) {
        return;
    }

    resultsSection.classList.add(
        "hidden"
    );

    loadingSection.classList.remove(
        "hidden"
    );

    analyzeButton.disabled =
        true;

    startTimer();
    startProgress();

    loadingSection.scrollIntoView({
        behavior: "smooth",
        block: "center"
    });


    const formData =
        new FormData();

    formData.append(
        "file",
        selectedFile
    );


    try {

        const response =
            await fetch(
                "/analyze",
                {
                    method: "POST",
                    body: formData
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Product analysis failed."
            );
        }
        finishProgress();
        renderResults(data);
        
        await new Promise(
        resolve =>
            setTimeout(
                resolve,
                450
            )
    );

        loadingSection.classList.add(
            "hidden"
        );

        resultsSection.classList.remove(
            "hidden"
        );


        resultsSection.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    }
    catch (error) {
        if (progressInterval) {

        clearInterval(
            progressInterval
        );

        progressInterval = null;
        }

        loadingSection.classList.add(
            "hidden"
        );

        alert(
            "Analysis failed: " +
            error.message
        );

    }
    finally {

        stopTimer();

        analyzeButton.disabled =
            false;
    }
}


// ==========================================
// TIMER
// ==========================================

function startTimer() {

    let seconds = 0;

    elapsedTime.textContent =
        "0s";


    timerInterval =
        setInterval(
            () => {

                seconds++;

                elapsedTime.textContent =
                    `${seconds}s`;

            },
            1000
        );
}


function stopTimer() {

    if (timerInterval) {

        clearInterval(
            timerInterval
        );

        timerInterval =
            null;
    }
}


// ==========================================
// RESULTS
// ==========================================

function renderResults(data) {

    const product =
        data.product || {};

    const compliance =
        data.compliance || {};

    renderOverallStatus(
        compliance.summary || {}
    );

    renderSummary(
        compliance.summary || {}
    );

    renderCompliance(
        compliance.checks || []
    );

    renderProductInformation(
        product
    );
}


// ==========================================
// OVERALL STATUS
// ==========================================

function renderOverallStatus(summary) {

    const card =
        document.getElementById(
            "overallStatusCard"
        );

    const status =
        document.getElementById(
            "overallStatus"
        );

    const description =
        document.getElementById(
            "overallDescription"
        );

    const icon =
        card.querySelector(
            ".overall-icon"
        );


    card.classList.remove(
        "compliant",
        "non-compliant"
    );


    if (
        (summary.non_compliant || 0) > 0
    ) {

        card.classList.add(
            "non-compliant"
        );

        status.textContent =
            "Non-Compliant";

        description.textContent =
            "One or more declarations were identified as non-compliant.";

        icon.textContent =
            "×";

        return;
    }


    if (
        (summary.review_required || 0) > 0
        ||
        (summary.cannot_determine || 0) > 0
    ) {

        status.textContent =
            "Review Required";

        description.textContent =
            "Some mandatory declarations could not be automatically verified from this image.";

        icon.textContent =
            "!";

        return;
    }


    card.classList.add(
        "compliant"
    );

    status.textContent =
        "Compliant";

    description.textContent =
        "All currently implemented compliance checks were successfully verified.";

    icon.textContent =
        "✓";
}


// ==========================================
// SUMMARY CARDS
// ==========================================

function renderSummary(summary) {

    const container =
        document.getElementById(
            "summaryCards"
        );

    container.innerHTML = "";


    const cards = [

        {
            label: "Compliant",
            value:
                summary.compliant || 0,
            color: "#16a34a"
        },

        {
            label: "Non-Compliant",
            value:
                summary.non_compliant || 0,
            color: "#dc2626"
        },

        {
            label: "Review Required",
            value:
                summary.review_required || 0,
            color: "#d97706"
        },

        {
            label: "Cannot Determine",
            value:
                summary.cannot_determine || 0,
            color: "#64748b"
        }

    ];


    cards.forEach(
        item => {

            const card =
                document.createElement(
                    "div"
                );

            card.className =
                "summary-card";

            card.style.setProperty(
                "--card-color",
                item.color
            );


            const number =
                document.createElement(
                    "div"
                );

            number.className =
                "summary-number";

            number.textContent =
                item.value;


            const label =
                document.createElement(
                    "div"
                );

            label.className =
                "summary-label";

            label.textContent =
                item.label;


            card.append(
                number,
                label
            );


            container.appendChild(
                card
            );
        }
    );
}


// ==========================================
// COMPLIANCE
// ==========================================

function renderCompliance(checks) {

    const container =
        document.getElementById(
            "complianceResults"
        );

    container.innerHTML = "";


    checks.forEach(
        check => {

            const row =
                document.createElement(
                    "div"
                );

            row.className =
                "compliance-row";


            const status =
                check.status ||
                "CANNOT_DETERMINE";


            const statusSlug =
                status
                    .toLowerCase()
                    .replaceAll(
                        "_",
                        "-"
                    );


            const icon =
                document.createElement(
                    "div"
                );

            icon.className =
                `check-icon icon-${statusSlug}`;


            const icons = {

                COMPLIANT: "✓",

                NON_COMPLIANT: "×",

                REVIEW_REQUIRED: "!",

                CANNOT_DETERMINE: "?"
            };


            icon.textContent =
                icons[status] || "?";


            const name =
                document.createElement(
                    "div"
                );

            name.className =
                "check-name";

            name.textContent =
                check.field || "Field";


            const reason =
                document.createElement(
                    "div"
                );

            reason.className =
                "check-reason";

            reason.textContent =
                check.reason || "";


            const badge =
                document.createElement(
                    "div"
                );

            badge.className =
                `status-badge status-${statusSlug}`;

            badge.textContent =
                prettyStatus(
                    status
                );


            row.append(
                icon,
                name,
                reason,
                badge
            );


            container.appendChild(
                row
            );
        }
    );
}


function prettyStatus(status) {

    return status
        .replaceAll("_", " ")
        .replace(
            /\b\w/g,
            char =>
                char.toUpperCase()
        );
}


// ==========================================
// PRODUCT INFORMATION
// ==========================================

function renderProductInformation(product) {

    const container =
        document.getElementById(
            "productInformation"
        );

    container.innerHTML = "";


    // ------------------------------------
    // PRODUCT IDENTITY
    // ------------------------------------

    const identity =
        createSection(
            "◉",
            "Product Identity"
        );


    const identityGrid =
        createInfoGrid();


    identityGrid.appendChild(
        createFieldCard(
            "Brand Name",
            getFieldValue(
                product.brand_name
            ),
            product.brand_name
        )
    );


    identityGrid.appendChild(
        createFieldCard(
            "Food / Product Name",
            getFieldValue(
                product.food_name
            ),
            product.food_name
        )
    );


    identity.appendChild(
        identityGrid
    );

    container.appendChild(
        identity
    );


    // ------------------------------------
    // PACKAGE DECLARATIONS
    // ------------------------------------

    const packageSection =
        createSection(
            "▣",
            "Package Declarations"
        );


    const packageGrid =
        createInfoGrid();


    packageGrid.appendChild(
        createFieldCard(
            "Net Quantity",
            formatQuantity(
                product.net_weight
            ),
            product.net_weight
        )
    );


    packageGrid.appendChild(
        createFieldCard(
            "MRP",
            formatMRP(
                product.mrp
            ),
            product.mrp
        )
    );


    packageGrid.appendChild(
        createFieldCard(
            "Manufacturing Date",
            getFieldValue(
                product.manufacturing_date
            ),
            product.manufacturing_date
        )
    );


    packageGrid.appendChild(
        createFieldCard(
            "Packing Date",
            getFieldValue(
                product.packing_date
            ),
            product.packing_date
        )
    );


    packageGrid.appendChild(
        createFieldCard(
            "Best Before",
            getFieldValue(
                product.best_before
            ),
            product.best_before
        )
    );


    packageSection.appendChild(
        packageGrid
    );

    container.appendChild(
        packageSection
    );


    // ------------------------------------
    // MANUFACTURER
    // ------------------------------------

    const companySection =
        createSection(
            "⌂",
            "Manufacturer & Business Details"
        );


    const companyGrid =
        createInfoGrid();


    companyGrid.appendChild(
        createFieldCard(
            "Manufacturer",
            getFieldValue(
                product.manufacturer
            ),
            product.manufacturer
        )
    );


    const roles =
        (product.company_roles || [])
            .map(
                item =>
                    `${capitalize(item.role)}: ${item.value}`
            );


    companyGrid.appendChild(
        createFieldCard(
            "Detected Roles",
            roles.length
                ? roles.join(" · ")
                : null
        )
    );


    companySection.appendChild(
        companyGrid
    );

    container.appendChild(
        companySection
    );


    // ------------------------------------
    // FSSAI
    // ------------------------------------

    const fssaiNumbers =
        product.fssai_numbers || [];


    const fssaiSection =
        createSection(
            "✓",
            "FSSAI Licence Numbers"
        );


    if (fssaiNumbers.length) {

        const tagList =
            document.createElement(
                "div"
            );

        tagList.className =
            "tag-list";


        fssaiNumbers.forEach(
            item => {

                const tag =
                    document.createElement(
                        "div"
                    );

                tag.className =
                    "data-tag";

                tag.textContent =
                    item.value;

                tagList.appendChild(
                    tag
                );
            }
        );


        fssaiSection.appendChild(
            tagList
        );

    }
    else {

        fssaiSection.appendChild(
            createMissingText(
                "No FSSAI licence number detected"
            )
        );
    }


    container.appendChild(
        fssaiSection
    );


    // ------------------------------------
    // CONSUMER CARE
    // ------------------------------------

    const care =
        product.consumer_care || {};


    const careSection =
        createSection(
            "☎",
            "Consumer Care"
        );


    const careGrid =
        createInfoGrid();


    careGrid.appendChild(
        createFieldCard(
            "Phone",
            getListValues(
                care.phone
            )
        )
    );


    careGrid.appendChild(
        createFieldCard(
            "Email",
            getListValues(
                care.email
            )
        )
    );


    careGrid.appendChild(
        createFieldCard(
            "Website",
            getListValues(
                care.website
            )
        )
    );


    careSection.appendChild(
        careGrid
    );

    container.appendChild(
        careSection
    );


    // ------------------------------------
    // INGREDIENTS
    // ------------------------------------

    const ingredients =
        product.ingredients || [];


    const ingredientSection =
        createSection(
            "≡",
            "Ingredients"
        );


    if (ingredients.length) {

        ingredients.forEach(
            item => {

                const card =
                    document.createElement(
                        "div"
                    );

                card.className =
                    "ingredient-card";

                card.textContent =
                    item.value;

                ingredientSection.appendChild(
                    card
                );
            }
        );

    }
    else {

        ingredientSection.appendChild(
            createMissingText(
                "Ingredients could not be detected"
            )
        );
    }


    container.appendChild(
        ingredientSection
    );


    // ------------------------------------
    // NUTRITION
    // ------------------------------------

    const nutrition =
        product.nutrition || {};


    const nutritionSection =
        createSection(
            "▦",
            "Nutritional Information"
        );


    const nutritionKeys =
        Object.keys(
            nutrition
        );


    if (nutritionKeys.length) {

        const grid =
            document.createElement(
                "div"
            );

        grid.className =
            "nutrition-grid";


        nutritionKeys.forEach(
            key => {

                const item =
                    nutrition[key];


                const nutrient =
                    document.createElement(
                        "div"
                    );

                nutrient.className =
                    "nutrient";


                const name =
                    document.createElement(
                        "div"
                    );

                name.className =
                    "nutrient-name";

                name.textContent =
                    prettyLabel(
                        key
                    );


                const value =
                    document.createElement(
                        "div"
                    );

                value.className =
                    "nutrient-value";

                value.textContent =
                    `${item.value ?? "—"} ${item.unit || ""}`
                    .trim();


                nutrient.append(
                    name,
                    value
                );


                grid.appendChild(
                    nutrient
                );
            }
        );


        nutritionSection.appendChild(
            grid
        );

    }
    else {

        nutritionSection.appendChild(
            createMissingText(
                "Nutrition information could not be detected"
            )
        );
    }


    container.appendChild(
        nutritionSection
    );
}


// ==========================================
// UI HELPERS
// ==========================================

function createSection(
    icon,
    title
) {

    const section =
        document.createElement(
            "section"
        );

    section.className =
        "info-section";


    const heading =
        document.createElement(
            "div"
        );

    heading.className =
        "info-section-title";


    const iconElement =
        document.createElement(
            "span"
        );

    iconElement.textContent =
        icon;


    const text =
        document.createElement(
            "div"
        );

    text.textContent =
        title;


    heading.append(
        iconElement,
        text
    );


    section.appendChild(
        heading
    );


    return section;
}


function createInfoGrid() {

    const grid =
        document.createElement(
            "div"
        );

    grid.className =
        "info-grid";

    return grid;
}


function createFieldCard(
    label,
    value,
    field = null
) {

    const card =
        document.createElement(
            "div"
        );

    card.className =
        "info-card";


    const labelElement =
        document.createElement(
            "div"
        );

    labelElement.className =
        "info-label";

    labelElement.textContent =
        label;


    const valueElement =
        document.createElement(
            "div"
        );

    valueElement.className =
        "info-value";


    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {

        valueElement.textContent =
            "Not detected";

        valueElement.classList.add(
            "missing"
        );

    }
    else {

        valueElement.textContent =
            value;
    }


    card.append(
        labelElement,
        valueElement
    );


    if (
        field &&
        typeof field === "object" &&
        field.confidence !== undefined &&
        field.confidence > 0
    ) {

        const confidence =
            document.createElement(
                "div"
            );

        confidence.className =
            "confidence";

        confidence.textContent =
            `${Math.round(
                field.confidence * 100
            )}% OCR confidence`;


        card.appendChild(
            confidence
        );
    }


    return card;
}


function createMissingText(text) {

    const div =
        document.createElement(
            "div"
        );

    div.className =
        "info-value missing";

    div.textContent =
        text;

    return div;
}


// ==========================================
// DATA HELPERS
// ==========================================

function getFieldValue(field) {

    if (
        !field ||
        typeof field !== "object"
    ) {
        return null;
    }

    return (
        field.value !== undefined
            ? field.value
            : null
    );
}


function formatQuantity(field) {

    if (
        !field ||
        field.value === null ||
        field.value === undefined
    ) {
        return null;
    }

    return (
        `${field.value} ${field.unit || ""}`
    ).trim();
}


function formatMRP(field) {

    if (
        !field ||
        field.value === null ||
        field.value === undefined
    ) {
        return null;
    }

    return `₹${field.value}`;
}


function getListValues(list) {

    if (
        !Array.isArray(list) ||
        list.length === 0
    ) {
        return null;
    }

    const values =
        list
            .map(
                item =>
                    item?.value
            )
            .filter(Boolean);


    return values.length
        ? values.join(", ")
        : null;
}


function prettyLabel(text) {

    return text
        .replaceAll("_", " ")
        .replace(
            /\b\w/g,
            char =>
                char.toUpperCase()
        );
}


function capitalize(text) {

    if (!text) {
        return "";
    }

    return (
        text.charAt(0).toUpperCase()
        +
        text.slice(1)
    );
}


// ==========================================
// NEW SCAN
// ==========================================

newScanButton.addEventListener(
    "click",
    () => {

        resultsSection.classList.add(
            "hidden"
        );

        scannerSection.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    }
);