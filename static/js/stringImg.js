class StringImg{

    constructor(x, line_sequence, numberOfPins, radius){
        this.instance = x 
        let center = [x.width/2, x.height/2]
        this.pins = this.setUpPins(numberOfPins, radius, center)
        this.line_sequence = line_sequence
        console.log(line_sequence)
    }

    setUpPins(numberOfPins, radius, center){
        let pinDict = {}
        let angleInterval = 360/numberOfPins
        //console.log("Center: " + center, Radius )
        for(let i = 0; i < numberOfPins; i++){
            let x = center[0] + radius * Math.cos((angleInterval * i) * (Math.PI / 180))
            let y = center[1] + radius * Math.sin((angleInterval * i) * (Math.PI / 180))
            pinDict[i] = [x, y]
            this.instance.point(x, y)
        }
        return pinDict
    }

    drawNextLine(lineIndex){ 
        let startPin = parseInt(this.line_sequence[lineIndex])
        let endPin = parseInt(this.line_sequence[lineIndex + 1])
        console.log(this.pins[startPin][0], this.pins[startPin][1], this.pins[endPin][0], this.pins[endPin][1])
        this.instance.strokeWeight(0.1); 
        this.instance.line(this.pins[startPin][0], this.pins[startPin][1], this.pins[endPin][0], this.pins[endPin][1])
    }
}