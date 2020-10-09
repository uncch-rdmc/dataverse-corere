# This is to store our unused code, for now.

#For views, to add back in fields that are both required and disabled.
#Don't need this currently as I was able to relax the required fields
        # print(formset.__dict__)
        # formset_data_copy = formset.data.copy()
        # formset.data._mutable = True
        # sub_count = formset.data.get("file_submission-TOTAL_FORMS")
        # for i in range(int(sub_count)):
        #     notes_count = formset.data.get("note-file_submission-"+str(i)+"-notes-TOTAL_FORMS")
        #     for j in range(int(notes_count)):
        #         print("note-file_submission-"+str(i)+"-notes-"+str(j)+"-id")
        #         print(formset.data.get("note-file_submission-"+str(i)+"-notes-"+str(j)+"-id"))
        #         try:
        #             note_id = int(formset.data.get("note-file_submission-"+str(i)+"-notes-"+str(j)+"-id"))
        #         except ValueError:
        #             continue #new notes have no id, we skip those
        #         note_filt = m.Note.objects.filter(id=note_id) #We do a filt so it'll be lazy evaluated (hopefully)
        #         if(not "note-file_submission-"+str(i)+"-notes-"+str(j)+"-text" in formset.data):
        #             formset.data["note-file_submission-"+str(i)+"-notes-"+str(j)+"-text"] = note_filt[0].text
        #         #If we all other required fields to note, we need to update here as well