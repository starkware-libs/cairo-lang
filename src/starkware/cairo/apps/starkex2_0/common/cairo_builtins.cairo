# ***********************************************************************
# * This code is licensed under the Cairo Program License.              *
# * The license can be found in: licenses/CairoProgramLicense.txt       *
# ***********************************************************************

# A representation of a HashBuiltin struct, specifying the hash builtin memory structure.
struct HashBuiltin:
    member x : felt
    member y : felt
    member result : felt
end

# A representation of a SignatureBuiltin struct, specifying the signature builtin memory structure.
struct SignatureBuiltin:
    member pub_key : felt
    member message : felt
end
