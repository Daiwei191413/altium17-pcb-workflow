Function PadCsvText(Value : String) : String;
Var I : Integer;
Begin
    Result := '"';
    For I := 1 To Length(Value) Do Begin
        If Value[I] = '"' Then Result := Result + '"';
        Result := Result + Value[I];
    End;
    Result := Result + '"';
End;

Procedure ExportFootprintPads;
Var Lib : IPCB_Library;
    Footprint : IPCB_LibComponent;
    Iterator : IPCB_GroupIterator;
    Pad : IPCB_Pad;
    Rows : TStringList;
    Board : IPCB_Board;
    Folder, Stem, OutputFile : String;
    Sequence : Integer;
Begin
    Lib := PCBServer.GetCurrentPCBLibrary;
    Board := PCBServer.GetCurrentPCBBoard;
    If (Lib = Nil) Or (Board = Nil) Then Begin
        ShowMessage('Open the saved PcbLib and select the target footprint first.'); Exit;
    End;
    If (UpperCase(ExtractFileExt(Board.FileName)) <> '.PCBLIB') Or
       (Not FileExists(Board.FileName)) Then Begin
        ShowMessage('Run this from a saved PcbLib document.'); Exit;
    End;
    Footprint := Lib.CurrentComponent;
    If Footprint = Nil Then Begin ShowMessage('Select a library footprint first.'); Exit; End;
    Folder := ExtractFilePath(Board.FileName);
    If UpperCase(Copy(Folder, 1, 2)) <> 'D:' Then Folder := 'D:\Codex\Projects\';
    If Not DirectoryExists(Folder) Then Begin ShowMessage('Output directory unavailable: ' + Folder); Exit; End;
    Stem := Folder + ChangeFileExt(ExtractFileName(Board.FileName), '') + '_FootprintPads';
    OutputFile := Stem + '.csv'; Sequence := 1;
    While FileExists(OutputFile) Do Begin
        Inc(Sequence); OutputFile := Stem + '_' + IntToStr(Sequence) + '.csv';
    End;
    Rows := TStringList.Create;
    Try
        Rows.Add('footprint,pin,x_adcoord,y_adcoord,top_x_adcoord,top_y_adcoord,hole_adcoord,layer_id,top_shape_id,rotation_deg');
        Iterator := Footprint.GroupIterator_Create;
        Try
            Iterator.AddFilter_ObjectSet(MkSet(ePadObject));
            Pad := Iterator.FirstPCBObject;
            While Pad <> Nil Do Begin
                Rows.Add(PadCsvText(Footprint.Name) + ',' + PadCsvText(Pad.Name) + ',' +
                    IntToStr(Pad.X - Footprint.X) + ',' + IntToStr(Pad.Y - Footprint.Y) + ',' +
                    IntToStr(Pad.TopXSize) + ',' + IntToStr(Pad.TopYSize) + ',' +
                    IntToStr(Pad.HoleSize) + ',' + IntToStr(Pad.Layer) + ',' +
                    IntToStr(Pad.TopShape) + ',' + PadCsvText(FloatToStr(Pad.Rotation)));
                Pad := Iterator.NextPCBObject;
            End;
        Finally
            Footprint.GroupIterator_Destroy(Iterator);
        End;
        If Rows.Count < 2 Then Begin ShowMessage('No pads in the selected footprint.'); Exit; End;
        Rows.SaveToFile(OutputFile);
    Finally
        Rows.Free;
    End;
End;
