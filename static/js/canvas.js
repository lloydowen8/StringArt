window.onload = () => { 
    let dropArea = document.getElementById('drop-area')
    dropArea.addEventListener('drop', handleDrop, false);
}

let file;
let img;
let raw;

function handleDrop(e) {
  let dt = e.dataTransfer;
  let files = dt.files;

  handleFiles(files, setup);
}

function handleFiles(files, setup) {
    files = [...files];
    file = files[0];
    document.getElementById("upload-label").classList.add("hidden");
    let reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onloadend = function() {
        file = reader.result;
        raw = new Image();
        raw.src = file;
        raw.onload = function(){ 

            new p5(sketch);
        }

    }

    //files.forEach(uploadFile)
}

sketch = function(p){ 

    let sizeSlider = document.getElementById("imageSize");
    let parentDiv = document.getElementById("drop-area");
    let x = 100;
    let y = 100;
    let imgRatio;
    let interval;
    let data;

    function defineStringSketch(line_sequence, numPins){ 
        return function(x){ 
            x.setup = function(){ 
                let canvas =  x.createCanvas(600, 600);
                canvas.parent(document.getElementById("display-area"));
                stringImg = new StringImg(x, line_sequence, numPins, 300)
                lineIndex = 0
                console.log(numPins)
                
            }
        
            x.draw = function(){ 
                if(lineIndex < line_sequence.length - 1){ 
                    stringImg.drawNextLine(lineIndex)
                    lineIndex++
                }

            }
        }
    }

    

    p.setup = function (){

        let canvas =  p.createCanvas(parentDiv.clientWidth, parentDiv.clientHeight);
        canvas.parent(document.getElementById("image-form"));

        img = p.createImage(raw.width, raw.height);
        img.drawingContext.drawImage(raw, 0, 0);
        imgRatio = img.width / img.height;
        document.getElementById("drop-area").style.width = 500 * imgRatio;

        let form = document.getElementById("param-form");
        form.onsubmit = (e) => { 
            e.preventDefault();

            data = new FormData(form);
            let cropImg = img.get((x - sizeSlider.value/2) * (img.width / canvas.width), (y - sizeSlider.value/2) * (img.height / canvas.height), sizeSlider.value * (img.width / canvas.width), sizeSlider.value * (img.height / canvas.height));
            let testImg = document.createElement("img");
            testImg.src = cropImg.canvas.toDataURL();
            document.getElementById("display-area").appendChild(testImg);
            data.append("image", cropImg.canvas.toDataURL());

            fetch("/fileUpload", {
                method: 'POST',
                body: data
            }).then(function(response){
                response.text().then(function(text){ 
                    let data = JSON.parse(text)
                    document.getElementById("drop-area").classList.add("hidden")
                    document.getElementById("loading-area").classList.remove("hidden")
                    interval = setInterval(check_progress, 1000, data.thread_id, getStringJSON)

                })

            }).catch(() => { /* Error. Inform the user */ })
        }

        function check_progress(task_id, callback) {
            fetch("/progress/" + task_id, {
                method: 'GET',
            }).then(function(response){
                response.text().then(function(progress){ 
                    console.log(parseFloat(progress))
                    document.getElementById("progress-bar").style.width = parseFloat(progress) * 100 + "%"
                    if(parseInt(progress) == 1){
                        clearInterval(interval)
                        document.getElementById("loading-area").classList.add("hidden")
                        document.getElementById("display-area").classList.remove("hidden")
                        callback(task_id)
                    }
                })
                setTimeout(1000)
            }).catch(() => { 
                clearInterval(interval);
             })
        }

        function getStringJSON(task_id){ 
            fetch("/line_sequence/" + task_id, { 
                method:'GET',
            }).then(function(response){ 
                response.text().then(function(value){ 
                    line_sequence = JSON.parse(value).line_sequence
                    let string = defineStringSketch(line_sequence, parseInt(data.get('numPins')))
                    let stringDraw = new p5(string)
                })
            })
        }
        
    }
    
    p.draw = function(){
        p.clear();
        
        
        p.resizeCanvas(500 * imgRatio, 500);
        p.image(img, 0, 0, 500 * imgRatio, 500);

        if(p.dist(x,y, p.mouseX, p.mouseY) < sizeSlider.value / 2) {
            p.cursor(p.HAND);
            if(p.mouseIsPressed) {
                x = p.mouseX;
                y = p.mouseY;
                p.strokeWeight(5);
            } else {
                p.strokeWeight(2);
            }
            p.stroke(0);
        } else {
            p.cursor(p.ARROW);
            p.stroke(0);
        }
        p.noFill();
        p.circle(x, y, sizeSlider.value);
    }
}

