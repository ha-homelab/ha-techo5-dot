// Offline classifier parity harness. Reads little-endian float32 windows from
// stdin and writes one float32 score per window to stdout. Never opens a network
// or microphone. The tflite subpackage is unmodified release-tag TECHO5 source.
package main

import (
    "bufio"
    "encoding/binary"
    "fmt"
    "io"
    "math"
    "os"
    "github.com/HuskerMinion/techo5/echod/tflite"
)

func run() error {
    if len(os.Args) != 2 { return fmt.Errorf("usage: wakeparity model.tflite") }
    raw, err := os.ReadFile(os.Args[1]); if err != nil { return err }
    model, err := tflite.Parse(raw); if err != nil { return err }
    in, err := tflite.New(model); if err != nil { return err }
    shape := in.Input(0).Shape
    if len(shape) != 3 || shape[0] != 1 || shape[1] != 16 || shape[2] != 96 {
        return fmt.Errorf("unexpected input shape: %v", shape)
    }
    r, w := bufio.NewReader(os.Stdin), bufio.NewWriter(os.Stdout)
    defer w.Flush()
    frame, score := make([]byte, 16*96*4), make([]byte, 4)
    for {
        n, err := io.ReadFull(r, frame)
        if err == io.EOF && n == 0 { return nil }
        if err != nil { return err }
        for j := range in.Input(0).F32 { in.Input(0).F32[j] = math.Float32frombits(binary.LittleEndian.Uint32(frame[j*4:])) }
        if err := in.Invoke(); err != nil { return err }
        out := in.Output(0)
        if len(out.F32) != 1 { return fmt.Errorf("unexpected output shape: %v", out.Shape) }
        value := out.F32[0]
        if math.IsNaN(float64(value)) || math.IsInf(float64(value), 0) { return fmt.Errorf("non-finite score") }
        binary.LittleEndian.PutUint32(score, math.Float32bits(value))
        if _, err := w.Write(score); err != nil { return err }
        // Flush each window so a bounded caller can stream without pipe deadlock.
        if err := w.Flush(); err != nil { return err }
    }
}

func main() { if err := run(); err != nil { fmt.Fprintln(os.Stderr, err); os.Exit(1) } }
