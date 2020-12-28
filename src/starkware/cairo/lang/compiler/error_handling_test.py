from starkware.cairo.lang.compiler.error_handling import InputFile, Location, LocationError


def test_location_error():
    content = """\
First line,
second line.
"""
    location = Location(
        start_line=2,
        start_col=8,
        end_line=2,
        end_col=12,
        input_file=InputFile(
            filename='file.cairo',
            content=content))

    expected_message = 'file.cairo:2:8: Error message.'
    expected_message_with_content = f"""\
{expected_message}
second line.
       ^**^\
"""
    assert location.to_string('Error message.') == expected_message
    assert str(location) == 'file.cairo:2:8'
    assert location.to_string_with_content('Error message.') == expected_message_with_content
    assert str(LocationError('Error message.', location=location)) == expected_message_with_content

    err2 = LocationError(message='Error message.', location=None)
    err2.notes.append('note1')
    err2.notes.append('note2')
    assert str(err2) == """\
Error message.
note1
note2"""
