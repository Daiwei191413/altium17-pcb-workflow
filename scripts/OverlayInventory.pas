Function CsvText(Value : String) : String;
Var I : Integer;
    S : String;
Begin
    S := '"';
    For I := 1 To Length(Value) Do Begin
        If Value[I] = '"' Then S := S + '"';
        S := S + Value[I];
    End;
    Result := S + '"';
End;

Procedure AddTrack(Lines : TStringList; Kind, RefDes, Pattern : String; T : IPCB_Track);
Begin
    Lines.Add(Kind + ',' + CsvText(RefDes) + ',' + CsvText(Pattern) + ',,' +
        IntToStr(T.X1) + ',' + IntToStr(T.Y1) + ',' + IntToStr(T.X2) + ',' +
        IntToStr(T.Y2) + ',' + IntToStr(T.Width));
End;

Procedure WriteOverlayInventory(B : IPCB_Board; OutputFile : String);
Var Components, Tracks : IPCB_BoardIterator;
    Members : IPCB_GroupIterator;
    C : IPCB_Component;
    T : IPCB_Track;
    Lines : TStringList;
    N : Integer;
Begin
    Lines := TStringList.Create;
    Try
        Lines.Add('kind,designator,footprint,track_count,x1_adcoord,y1_adcoord,x2_adcoord,y2_adcoord,width_adcoord');
        Components := B.BoardIterator_Create;
        Try
            Components.AddFilter_ObjectSet(MkSet(eComponentObject));
            Components.AddFilter_LayerSet(AllLayers);
            Components.AddFilter_Method(eProcessAll);
            C := Components.FirstPCBObject;
            While C <> Nil Do Begin
                N := 0;
                Members := C.GroupIterator_Create;
                Try
                    Members.AddFilter_LayerSet(MkSet(eTopOverlay));
                    Members.AddFilter_ObjectSet(MkSet(eTrackObject));
                    T := Members.FirstPCBObject;
                    While T <> Nil Do Begin
                        If T.Layer = eTopOverlay Then Begin
                            AddTrack(Lines, 'member', C.Name.Text, C.Pattern, T);
                            Inc(N);
                        End;
                        T := Members.NextPCBObject;
                    End;
                Finally
                    C.GroupIterator_Destroy(Members);
                End;
                Lines.Add('component,' + CsvText(C.Name.Text) + ',' + CsvText(C.Pattern) + ',' + IntToStr(N) + ',,,,,');
                C := Components.NextPCBObject;
            End;
        Finally
            B.BoardIterator_Destroy(Components);
        End;
        Tracks := B.BoardIterator_Create;
        Try
            Tracks.AddFilter_LayerSet(MkSet(eTopOverlay));
            Tracks.AddFilter_ObjectSet(MkSet(eTrackObject));
            Tracks.AddFilter_Method(eProcessAll);
            T := Tracks.FirstPCBObject;
            While T <> Nil Do Begin
                If (T.Layer = eTopOverlay) And (Not T.InComponent) Then
                    AddTrack(Lines, 'free', '', '', T);
                T := Tracks.NextPCBObject;
            End;
        Finally
            B.BoardIterator_Destroy(Tracks);
        End;
        Lines.SaveToFile(OutputFile);
    Finally
        Lines.Free;
    End;
End;

Procedure ExportTopOverlayInventory;
Var B : IPCB_Board;
    SourceFile, Folder, Stem, Dest : String;
    N : Integer;
Begin
    B := PCBServer.GetCurrentPCBBoard;
    If B = Nil Then Begin ShowMessage('Open the target PcbDoc in the PCB editor.'); Exit; End;
    SourceFile := B.FileName;
    If (UpperCase(ExtractFileExt(SourceFile)) <> '.PCBDOC') Or (Not FileExists(SourceFile)) Then Begin
        ShowMessage('Open a saved PcbDoc, then run the inventory again.'); Exit;
    End;
    Folder := ExtractFilePath(SourceFile);
    If UpperCase(Copy(Folder, 1, 2)) <> 'D:' Then Folder := 'D:\Codex\Projects\';
    Stem := Folder + ChangeFileExt(ExtractFileName(SourceFile), '') + '_TopOverlay';
    Dest := Stem + '.csv';
    N := 1;
    While FileExists(Dest) Do Begin Inc(N); Dest := Stem + '_' + IntToStr(N) + '.csv'; End;
    WriteOverlayInventory(B, Dest);
    ShowMessage('Top Overlay track inventory saved to ' + Dest);
End;
